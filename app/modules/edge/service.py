"""Edge Gateway iş mantığı.

Outbound-only gateway network kurgusu (bkz. docs/adr/0009-edge-gateway-network):
- enroll: cihaz kendini tanıtır (public key) -> pending
- status: cihaz onay durumunu sorgular (imzalı cihaz JWT'si ile)
- ingest: onaylı cihaz okuma gönderir -> kirli_kiyafetler (islem iş mantığı yeniden kullanılır)
- approve/revoke: admin onay/iptal
"""
import json
from datetime import datetime, timezone
from typing import Optional

from jose import jwt, JWTError
from fastapi import Request
from sqlalchemy.orm import Session

from ... import models
from ...utils import get_client_ip, write_audit_log
from ...exceptions import AuthException, BusinessLogicException, NotFoundException, PermissionException
from ..islem import repository as islem_repo
from . import repository, schemas

EDGE_JWT_ALGORITHM = "RS256"


# ---------------------------------------------------------------------------
# Kimlik doğrulama — cihaz JWT'si
# ---------------------------------------------------------------------------

def authenticate_device(db: Session, authorization: Optional[str]) -> models.EdgeDevice:
    """`Authorization: Bearer <cihaz_jwt>` başlığını doğrular.

    JWT, cihazın özel anahtarıyla RS256 imzalanmıştır; saklı public key ile
    doğrulanır. `sub=device_uid`, `type=edge` beklenir.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthException("Cihaz kimlik başlığı eksik.", details={"code_hint": "EDGE_AUTH_INVALID"})
    token = authorization.split(" ", 1)[1].strip()

    try:
        unverified = jwt.get_unverified_claims(token)
        device_uid = unverified.get("sub")
    except Exception:
        raise AuthException("Cihaz token'ı çözümlenemedi.")

    if not device_uid:
        raise AuthException("Cihaz token'ında sub yok.")

    device = repository.get_device_by_uid(db, device_uid)
    if not device or not device.public_key:
        raise AuthException("Cihaz bulunamadı veya kayıtlı değil.")

    try:
        payload = jwt.decode(token, device.public_key, algorithms=[EDGE_JWT_ALGORITHM])
    except JWTError:
        raise AuthException("Cihaz token imzası geçersiz veya süresi dolmuş.")

    if payload.get("type") != "edge":
        raise AuthException("Geçersiz cihaz token tipi.")

    return device


# ---------------------------------------------------------------------------
# Enroll
# ---------------------------------------------------------------------------

def enroll(db: Session, request: Request, req: schemas.EnrollRequest) -> dict:
    ip = get_client_ip(request)
    hardware_json = json.dumps([h.model_dump() for h in req.hardware]) if req.hardware else None
    existing = repository.get_device_by_uid(db, req.device_uid)

    if existing is None:
        device = models.EdgeDevice(
            device_uid=req.device_uid,
            name=req.name,
            location=req.location,
            public_key=req.public_key,
            status="pending",
            agent_version=req.agent_version,
            hardware=hardware_json,
            enrolled_at=datetime.now(timezone.utc),
        )
        repository.add_device(db, device)
        write_audit_log(db, action="EDGE_ENROLL", username=None,
                        detail=f"Yeni edge cihaz kaydı: {req.device_uid} ({req.name})",
                        ip_address=ip, status="success")
        return {"data": {"device_uid": device.device_uid, "status": device.status}}

    # İdempotent: public key aynıysa mevcut durumu döndür.
    # Public key değiştiyse güvenlik gereği yeniden onaya düşür (bkz. docs/08_SECURITY).
    if existing.public_key != req.public_key:
        existing.public_key = req.public_key
        existing.status = "pending"
        existing.approved_at = None
        existing.approved_by_user_id = None
        existing.name = req.name or existing.name
        existing.location = req.location or existing.location
        existing.agent_version = req.agent_version or existing.agent_version
        existing.hardware = hardware_json or existing.hardware
        repository.commit(db)
        write_audit_log(db, action="EDGE_ENROLL", username=None,
                        detail=f"Edge cihaz public key değişti, yeniden onaya düştü: {req.device_uid}",
                        ip_address=ip, status="success")
    return {"data": {"device_uid": existing.device_uid, "status": existing.status}}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_status(db: Session, device: models.EdgeDevice) -> dict:
    repository.touch_last_seen(db, device)
    return {"data": {
        "device_uid": device.device_uid,
        "status": device.status,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }}


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest(db: Session, request: Request, device: models.EdgeDevice, req: schemas.IngestRequest) -> dict:
    if device.status != "approved":
        raise PermissionException("Cihaz onaylı değil; veri kabul edilmez.")

    ip = get_client_ip(request)
    results = []
    accepted = 0
    rejected = 0

    for reading in req.readings:
        # İdempotency: bu okuma daha önce işlendiyse tekrar yazma.
        receipt = repository.get_receipt(db, reading.client_reading_id)
        if receipt:
            results.append({
                "client_reading_id": reading.client_reading_id,
                "status": "duplicate",
                "islem_id": receipt.islem_id,
            })
            continue

        if reading.islem_tipi != "kirli":
            results.append({"client_reading_id": reading.client_reading_id,
                            "status": "rejected", "reason": "UNSUPPORTED_ISLEM_TIPI"})
            rejected += 1
            continue

        # İş mantığı yeniden kullanımı: RFID kayıtlı mı? (islem.process_islem deseni)
        kiyafet = islem_repo.get_kiyafet_by_rfid(db, reading.rfid_tag)
        if not kiyafet:
            db.add(models.EdgeReadingReceipt(
                client_reading_id=reading.client_reading_id, device_id=device.id,
                rfid_tag=reading.rfid_tag, islem_id=None, status="rejected",
            ))
            db.commit()
            results.append({"client_reading_id": reading.client_reading_id,
                            "status": "rejected", "reason": "RFID_NOT_REGISTERED"})
            rejected += 1
            continue

        read_at = reading.read_at or datetime.now(timezone.utc)
        yeni = models.Kirli_Kiyafet(
            rfid_tag=reading.rfid_tag,
            sicil_numarasi=kiyafet.sicil_numarasi,
            zaman_damgasi=read_at,
        )
        db.add(yeni)
        db.flush()  # islem_id üret
        db.add(models.EdgeReadingReceipt(
            client_reading_id=reading.client_reading_id, device_id=device.id,
            rfid_tag=reading.rfid_tag, islem_id=yeni.islem_id, status="accepted",
        ))
        db.commit()
        results.append({"client_reading_id": reading.client_reading_id,
                        "status": "accepted", "islem_id": yeni.islem_id})
        accepted += 1

    repository.touch_last_seen(db, device)
    write_audit_log(db, action="EDGE_INGEST", username=None,
                    detail=f"Edge {device.device_uid}: {accepted} kabul, {rejected} red",
                    ip_address=ip, status="success")
    return {"data": {"results": results, "accepted": accepted, "rejected": rejected}}


# ---------------------------------------------------------------------------
# Admin: list / approve / revoke
# ---------------------------------------------------------------------------

def list_devices(db: Session, status: Optional[str] = None) -> dict:
    devices = repository.list_devices(db, status)
    out = []
    for d in devices:
        item = schemas.EdgeDeviceOut.model_validate(d).model_dump()
        try:
            item["hardware"] = json.loads(d.hardware) if d.hardware else None
        except (ValueError, TypeError):
            item["hardware"] = None
        out.append(item)
    return {"data": out}


def approve_device(db: Session, request: Request, device_id: int, current_user: models.User) -> dict:
    device = repository.get_device_by_id(db, device_id)
    if not device:
        raise NotFoundException("Edge Cihaz")
    device.status = "approved"
    device.approved_at = datetime.now(timezone.utc)
    device.approved_by_user_id = current_user.id
    repository.commit(db)
    write_audit_log(db, action="EDGE_APPROVE", username=current_user.username,
                    detail=f"Edge cihaz onaylandı: {device.device_uid}",
                    ip_address=get_client_ip(request), status="success")
    return {"data": {"device_uid": device.device_uid, "status": device.status}}


def revoke_device(db: Session, request: Request, device_id: int, current_user: models.User) -> dict:
    device = repository.get_device_by_id(db, device_id)
    if not device:
        raise NotFoundException("Edge Cihaz")
    device.status = "revoked"
    repository.commit(db)
    write_audit_log(db, action="EDGE_REVOKE", username=current_user.username,
                    detail=f"Edge cihaz iptal edildi: {device.device_uid}",
                    ip_address=get_client_ip(request), status="success")
    return {"data": {"device_uid": device.device_uid, "status": device.status}}
