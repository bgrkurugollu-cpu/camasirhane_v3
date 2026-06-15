"""Edge Gateway modülü testleri (docs/adr/0009-edge-gateway-network).

enroll -> pending, onaysız ingest reddi, approve sonrası ingest yazımı,
RFID kayıtsız reddi, revoke engeli, idempotency ve cihaz JWT doğrulaması.
"""
import uuid
from datetime import datetime, timezone, timedelta

from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.models import EdgeDevice, Kirli_Kiyafet

CSRF = {"x-csrf-token": "test"}
CSRF_COOKIE = {"csrf_token": "test"}


def _gen_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv, pub


def _device_jwt(priv, device_uid, minutes=5):
    now = datetime.now(timezone.utc)
    payload = {"sub": device_uid, "type": "edge", "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, priv, algorithm="RS256")


def _enroll(client, device_uid, pub, name="Test Edge"):
    return client.post("/api/v1/edge/enroll", json={
        "device_uid": device_uid, "name": name, "location": "Test",
        "public_key": pub, "agent_version": "1.0.0",
        "hardware": [{"type": "reader", "model": "RRU9816", "transport": "tcp"}],
    })


def _auth(priv, device_uid):
    return {"Authorization": f"Bearer {_device_jwt(priv, device_uid)}"}


def _admin_csrf(token):
    return {"Authorization": f"Bearer {token}", **CSRF}


def test_enroll_creates_pending(client, db_session):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    r = _enroll(client, uid, pub)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "pending"
    dev = db_session.query(EdgeDevice).filter_by(device_uid=uid).first()
    assert dev is not None and dev.status == "pending"


def test_enroll_idempotent_same_key(client):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    r2 = _enroll(client, uid, pub)
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "pending"


def test_ingest_rejected_when_pending(client):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    r = client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json={
        "readings": [{"client_reading_id": str(uuid.uuid4()), "rfid_tag": "RFID-TEST"}]
    })
    assert r.status_code == 403


def _approve(client, admin_token, uid):
    dev_id = None
    listing = client.get("/api/v1/edge/devices", headers={"Authorization": f"Bearer {admin_token}"})
    for d in listing.json()["data"]:
        if d["device_uid"] == uid:
            dev_id = d["id"]
    assert dev_id is not None
    return client.post(f"/api/v1/edge/devices/{dev_id}/approve",
                       headers=_admin_csrf(admin_token), cookies=CSRF_COOKIE)


def test_approve_then_ingest_writes_kirli(client, db_session, admin_token):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    ar = _approve(client, admin_token, uid)
    assert ar.status_code == 200 and ar.json()["data"]["status"] == "approved"

    crid = str(uuid.uuid4())
    r = client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json={
        "readings": [{"client_reading_id": crid, "rfid_tag": "RFID-TEST"}]
    })
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["accepted"] == 1 and body["results"][0]["status"] == "accepted"
    # kirli_kiyafetler'e yazıldı mı?
    rec = db_session.query(Kirli_Kiyafet).filter_by(rfid_tag="RFID-TEST").first()
    assert rec is not None and rec.sicil_numarasi == "9999"


def test_ingest_rejected_rfid_not_registered(client, admin_token):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    _approve(client, admin_token, uid)
    r = client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json={
        "readings": [{"client_reading_id": str(uuid.uuid4()), "rfid_tag": "YOK-123"}]
    })
    assert r.status_code == 200
    res = r.json()["data"]
    assert res["rejected"] == 1
    assert res["results"][0]["reason"] == "RFID_NOT_REGISTERED"


def test_ingest_idempotent_duplicate(client, db_session, admin_token):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    _approve(client, admin_token, uid)
    crid = str(uuid.uuid4())
    payload = {"readings": [{"client_reading_id": crid, "rfid_tag": "RFID-TEST"}]}
    client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json=payload)
    r2 = client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json=payload)
    assert r2.json()["data"]["results"][0]["status"] == "duplicate"
    # yalnızca tek kirli kayıt
    cnt = db_session.query(Kirli_Kiyafet).filter_by(rfid_tag="RFID-TEST").count()
    assert cnt == 1


def test_revoke_blocks_ingest(client, admin_token):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    _approve(client, admin_token, uid)
    # revoke
    listing = client.get("/api/v1/edge/devices", headers={"Authorization": f"Bearer {admin_token}"})
    dev_id = next(d["id"] for d in listing.json()["data"] if d["device_uid"] == uid)
    client.post(f"/api/v1/edge/devices/{dev_id}/revoke", headers=_admin_csrf(admin_token), cookies=CSRF_COOKIE)
    r = client.post("/api/v1/edge/ingest", headers=_auth(priv, uid), json={
        "readings": [{"client_reading_id": str(uuid.uuid4()), "rfid_tag": "RFID-TEST"}]
    })
    assert r.status_code == 403


def test_status_reports_state(client, admin_token):
    priv, pub = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    r = client.get("/api/v1/edge/status", headers=_auth(priv, uid))
    assert r.status_code == 200 and r.json()["data"]["status"] == "pending"
    _approve(client, admin_token, uid)
    r2 = client.get("/api/v1/edge/status", headers=_auth(priv, uid))
    assert r2.json()["data"]["status"] == "approved"


def test_invalid_device_jwt_rejected(client):
    priv, pub = _gen_keypair()
    other_priv, _ = _gen_keypair()
    uid = str(uuid.uuid4())
    _enroll(client, uid, pub)
    # Başka anahtarla imzalanmış token -> imza doğrulanmaz
    bad = {"Authorization": f"Bearer {_device_jwt(other_priv, uid)}"}
    r = client.get("/api/v1/edge/status", headers=bad)
    assert r.status_code == 401


def test_devices_list_requires_admin(client, user_token):
    r = client.get("/api/v1/edge/devices", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403
