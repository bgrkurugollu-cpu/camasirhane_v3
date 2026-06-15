from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from ... import database, models, security
from . import service, schemas

router = APIRouter(prefix="/edge", tags=["Edge"])


# ---------------------------------------------------------------------------
# Cihaz uçları (makine-makine) — CSRF muaf (bkz. main.py CSRFMiddleware)
# Kimlik: enroll açık, status/ingest cihaz JWT'si ile.
# ---------------------------------------------------------------------------

@router.post("/enroll")
def enroll(request: Request, req: schemas.EnrollRequest, db: Session = Depends(database.get_db)):
    return service.enroll(db, request, req)


def _device_dep(db: Session = Depends(database.get_db), authorization: Optional[str] = Header(None)):
    return service.authenticate_device(db, authorization)


@router.get("/status")
def status(device: models.EdgeDevice = Depends(_device_dep), db: Session = Depends(database.get_db)):
    return service.get_status(db, device)


@router.post("/ingest")
def ingest(
    request: Request,
    req: schemas.IngestRequest,
    device: models.EdgeDevice = Depends(_device_dep),
    db: Session = Depends(database.get_db),
):
    return service.ingest(db, request, device, req)


# ---------------------------------------------------------------------------
# Admin uçları (ana uygulama SPA) — normal kullanıcı JWT + CSRF + admin rol
# ---------------------------------------------------------------------------

@router.get("/devices")
def list_devices(
    status: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.require_admin),
):
    return service.list_devices(db, status)


@router.post("/devices/{device_id}/approve")
def approve_device(
    device_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.require_admin),
):
    return service.approve_device(db, request, device_id, current_user)


@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.require_admin),
):
    return service.revoke_device(db, request, device_id, current_user)
