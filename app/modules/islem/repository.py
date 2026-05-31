from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from ... import models
from typing import List, Tuple, Any

def get_kirli_siciller(db: Session) -> set:
    return {r.sicil_numarasi for r in db.query(models.Kirli_Kiyafet.sicil_numarasi).all()}

def get_aday_kayitlar(db: Session, kirli_siciller: set) -> List[Tuple[models.Kiyafet, models.Calisan]]:
    return (
        db.query(models.Kiyafet, models.Calisan)
        .join(models.Calisan, models.Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi)
        .filter(models.Kiyafet.sicil_numarasi.notin_(kirli_siciller))
        .all()
    )

def add_islem(db: Session, model_instance: Any):
    db.add(model_instance)
    db.flush()
    return model_instance

def commit_db(db: Session):
    db.commit()

def delete_islem(db: Session, model_instance: Any):
    db.delete(model_instance)
    db.flush()

def get_kiyafet_by_rfid(db: Session, rfid_tag: str) -> models.Kiyafet:
    return db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == rfid_tag).first()

def get_calisan_by_sicil(db: Session, sicil_numarasi: str) -> models.Calisan:
    return db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == sicil_numarasi).first()

def get_kirli_kayit_by_id(db: Session, islem_id: int) -> models.Kirli_Kiyafet:
    return db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.islem_id == islem_id).first()

def get_temiz_kayit_by_id(db: Session, islem_id: int) -> models.Temiz_Kiyafet:
    return db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.islem_id == islem_id).first()

def get_stats_counts(db: Session, bugun: datetime) -> Tuple[int, int, int]:
    kirli = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.zaman_damgasi >= bugun).count()
    temiz = db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.zaman_damgasi >= bugun).count()
    teslim = db.query(models.Teslim_Edilen).filter(models.Teslim_Edilen.zaman_damgasi >= bugun).count()
    return kirli, temiz, teslim

def get_raf_occupancy(db: Session):
    return db.query(models.Temiz_Kiyafet.raf_id, func.count(models.Temiz_Kiyafet.islem_id)).filter(models.Temiz_Kiyafet.raf_id != None).group_by(models.Temiz_Kiyafet.raf_id).all()

def get_raf_items(db: Session, rack_letter: str):
    return db.query(models.Temiz_Kiyafet, models.Calisan).outerjoin(models.Calisan, models.Temiz_Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi).filter(models.Temiz_Kiyafet.raf_id.like(f"{rack_letter}%")).all()

def get_history_records(db: Session, model: Any, start_date: datetime):
    return db.query(model).filter(model.zaman_damgasi >= start_date).all()

def get_tablo_rows(db: Session, model: Any, limit: int):
    return db.query(model, models.Calisan).outerjoin(models.Calisan, model.sicil_numarasi == models.Calisan.sicil_numarasi).order_by(model.zaman_damgasi.desc()).limit(limit).all()

def get_kiyafet_rows(db: Session, q: str, limit: int, offset: int):
    query = db.query(models.Kiyafet, models.Calisan).outerjoin(models.Calisan, models.Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(models.Kiyafet.rfid_tag.ilike(term), models.Kiyafet.sicil_numarasi.ilike(term), models.Calisan.ad.ilike(term), models.Calisan.soyad.ilike(term)))
    total = query.count()
    rows = query.order_by(models.Kiyafet.rfid_tag).offset(offset).limit(limit).all()
    return total, rows
