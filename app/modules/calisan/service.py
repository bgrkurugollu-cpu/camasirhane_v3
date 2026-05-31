from sqlalchemy.orm import Session
from ...exceptions import NotFoundException
from . import repository

def get_calisan(db: Session, sicil_numarasi: str):
    calisan = repository.get_calisan_by_sicil(db, sicil_numarasi)
    if not calisan:
        raise NotFoundException("Çalışan")
    return {
        "sicil_numarasi": calisan.sicil_numarasi,
        "ad": calisan.ad,
        "soyad": calisan.soyad,
        "cinsiyet": calisan.cinsiyet
    }
