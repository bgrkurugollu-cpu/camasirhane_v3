from sqlalchemy.orm import Session
from ... import models

def get_calisan(db: Session, sicil_numarasi: str):
    return db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == sicil_numarasi).first()

def add_calisan(db: Session, calisan: models.Calisan):
    db.add(calisan)
    db.commit()
    db.refresh(calisan)
    return calisan

def get_kiyafet(db: Session, rfid_tag: str):
    return db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == rfid_tag).first()

def add_kiyafet(db: Session, kiyafet: models.Kiyafet):
    db.add(kiyafet)
    db.commit()
    return kiyafet

def update_kiyafet_tags(db: Session, old_tag: str, new_tag: str, new_sicil: str):
    db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == old_tag).update(
        {models.Kiyafet.rfid_tag: new_tag, models.Kiyafet.sicil_numarasi: new_sicil}
    )
    db.commit()

def commit_db(db: Session):
    db.commit()

def delete_kiyafet(db: Session, kiyafet: models.Kiyafet):
    db.delete(kiyafet)
    db.commit()
