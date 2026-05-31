from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ... import models, database, security
from . import service

router = APIRouter(prefix="/calisan", tags=["Calisan"])

@router.get("/{sicil_numarasi}", response_model=dict)
def get_calisan(
    sicil_numarasi: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.get_calisan(db, sicil_numarasi)
