from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from . import models

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def write_audit_log(
    db: Session,
    action: str,
    username: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success"
):
    log = models.AuditLog(
        action=action,
        username=username,
        detail=detail,
        ip_address=ip_address,
        status=status,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
