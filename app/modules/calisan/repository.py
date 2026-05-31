from sqlalchemy.orm import Session
from ... import models

def get_calisan_by_sicil(db: Session, sicil_numarasi: str) -> models.Calisan:
    return db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == sicil_numarasi).first()
