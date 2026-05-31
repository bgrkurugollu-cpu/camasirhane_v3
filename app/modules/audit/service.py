from sqlalchemy.orm import Session
from typing import Optional
from ... import models
from ...exceptions import PermissionException
from . import repository

def get_audit_logs(db: Session, limit: int, username: Optional[str], action: Optional[str], current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler audit loglarını görebilir.")
    return repository.get_audit_logs(db, limit, username, action)
