from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from ... import models, schemas, database, security
from . import service

router = APIRouter(prefix="/audit-logs", tags=["Audit"])

@router.get("", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
    limit: int = 100,
    username: Optional[str] = None,
    action: Optional[str] = None
):
    return service.get_audit_logs(db, limit, username, action, current_user)
