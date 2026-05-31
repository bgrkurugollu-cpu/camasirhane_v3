from sqlalchemy.orm import Session
from typing import Optional
from ... import models

def get_audit_logs(db: Session, limit: int, username: Optional[str], action: Optional[str]):
    query = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc())
    if username:
        query = query.filter(models.AuditLog.username == username)
    if action:
        query = query.filter(models.AuditLog.action == action)
    return query.limit(limit).all()
