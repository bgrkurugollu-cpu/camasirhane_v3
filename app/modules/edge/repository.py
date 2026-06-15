from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ... import models


def get_device_by_uid(db: Session, device_uid: str):
    return db.query(models.EdgeDevice).filter(models.EdgeDevice.device_uid == device_uid).first()


def get_device_by_id(db: Session, device_id: int):
    return db.query(models.EdgeDevice).filter(models.EdgeDevice.id == device_id).first()


def list_devices(db: Session, status: str = None):
    q = db.query(models.EdgeDevice)
    if status:
        q = q.filter(models.EdgeDevice.status == status)
    return q.order_by(models.EdgeDevice.enrolled_at.desc()).all()


def add_device(db: Session, device: models.EdgeDevice):
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def commit(db: Session):
    db.commit()


def touch_last_seen(db: Session, device: models.EdgeDevice):
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()


def get_receipt(db: Session, client_reading_id: str):
    return (
        db.query(models.EdgeReadingReceipt)
        .filter(models.EdgeReadingReceipt.client_reading_id == client_reading_id)
        .first()
    )


def add_receipt(db: Session, receipt: models.EdgeReadingReceipt):
    db.add(receipt)
    # commit, çağıran servis tarafından (kirli kayıt ile aynı transaction) yapılır
    db.flush()
    return receipt
