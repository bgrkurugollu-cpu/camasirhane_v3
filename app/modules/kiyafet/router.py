from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ... import models, schemas, database, security
from . import service

router = APIRouter(prefix="/kiyafet", tags=["Kiyafet"])

@router.post("", response_model=dict)
def register_kiyafet(
    request: Request,
    req: schemas.KiyafetCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.register_kiyafet(db, request, req, current_user)

@router.put("/{old_rfid_tag}", response_model=dict)
def update_kiyafet(
    old_rfid_tag: str,
    req: schemas.KiyafetCreate,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.update_kiyafet(db, request, old_rfid_tag, req, current_user)

@router.delete("/{rfid_tag}", response_model=dict)
def delete_kiyafet(
    rfid_tag: str,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.delete_kiyafet(db, request, rfid_tag, current_user)
