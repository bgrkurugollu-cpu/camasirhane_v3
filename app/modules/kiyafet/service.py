from sqlalchemy.orm import Session
from fastapi import Request
from ... import models, schemas
from ...utils import get_client_ip, write_audit_log
from ...exceptions import BusinessLogicException, NotFoundException, PermissionException
from . import repository

def register_kiyafet(db: Session, request: Request, req: schemas.KiyafetCreate, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler RFID eşleştirmesi yapabilir.")
        
    ip = get_client_ip(request)
    calisan = repository.get_calisan(db, req.sicil_numarasi)
    
    if not calisan:
        if not req.ad or not req.soyad:
            raise BusinessLogicException("Yeni personel kaydı için Ad ve Soyad zorunludur.")
        yeni_calisan = models.Calisan(
            sicil_numarasi=req.sicil_numarasi, ad=req.ad, soyad=req.soyad, cinsiyet=req.cinsiyet
        )
        repository.add_calisan(db, yeni_calisan)
    
    existing = repository.get_kiyafet(db, req.rfid_tag)
    if existing:
        existing.sicil_numarasi = req.sicil_numarasi
        repository.commit_db(db)
        action_log = "RFID_UPDATE"
    else:
        yeni_kiyafet = models.Kiyafet(rfid_tag=req.rfid_tag, sicil_numarasi=req.sicil_numarasi)
        repository.add_kiyafet(db, yeni_kiyafet)
        action_log = "RFID_REGISTER"

    write_audit_log(
        db=db, action=action_log, username=current_user.username,
        detail=f"RFID: {req.rfid_tag} -> Sicil: {req.sicil_numarasi}", ip_address=ip, status="success"
    )
    return {"message": "RFID eşleştirmesi başarılı."}

def update_kiyafet(db: Session, request: Request, old_rfid_tag: str, req: schemas.KiyafetCreate, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler RFID eşleştirmesi güncelleyebilir.")
        
    kayit = repository.get_kiyafet(db, old_rfid_tag)
    if not kayit:
        raise NotFoundException("Kayıt")
        
    if old_rfid_tag != req.rfid_tag:
        conflict = repository.get_kiyafet(db, req.rfid_tag)
        if conflict:
             raise BusinessLogicException("Yeni girilen RFID Tag zaten başka bir sicille eşleşmiş.")
             
        repository.update_kiyafet_tags(db, old_rfid_tag, req.rfid_tag, req.sicil_numarasi)
    else:
        kayit.sicil_numarasi = req.sicil_numarasi
        repository.commit_db(db)
        
    write_audit_log(
        db=db, action="RFID_MATCH_UPDATE", 
        detail=f"Önceki: {old_rfid_tag} -> Yeni Tag: {req.rfid_tag}, Sicil: {req.sicil_numarasi}", 
        ip_address=get_client_ip(request), username=current_user.username
    )
    return {"status": "success"}

def delete_kiyafet(db: Session, request: Request, rfid_tag: str, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler RFID eşleştirmesi silebilir.")
        
    kayit = repository.get_kiyafet(db, rfid_tag)
    if not kayit:
        raise NotFoundException("Kayıt")
        
    repository.delete_kiyafet(db, kayit)
    write_audit_log(
        db=db, action="RFID_MATCH_DELETE", detail=f"Silinen: RFID Tag {rfid_tag}, Sicil: {kayit.sicil_numarasi}", 
        ip_address=get_client_ip(request), username=current_user.username
    )
    return {"status": "success"}
