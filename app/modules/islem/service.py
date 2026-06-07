from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from fastapi import Request
import random
from typing import Optional

from ... import models, schemas
from ...utils import get_client_ip, write_audit_log
from ...exceptions import BusinessLogicException, NotFoundException, PermissionException
from . import repository
from .shelf_service import assign_shelf, get_compartment_capacity, RACK_LETTERS, RACK_FLOORS, RACK_COMPARTMENTS

def process_rfid_oku(db: Session, request: Request, current_user: models.User):
    kirli_siciller = repository.get_kirli_siciller(db)
    aday_kayitlar = repository.get_aday_kayitlar(db, kirli_siciller)

    if not aday_kayitlar:
        return {"durum": "bos", "mesaj": "Kirli sepetinde yeni kıyafet bulunamadı!", "eklenenler": []}

    secilen = random.sample(aday_kayitlar, min(10, len(aday_kayitlar)))
    now_utc = datetime.now(timezone.utc)
    ip = get_client_ip(request)
    eklenenler = []

    for kiyafet, calisan in secilen:
        yeni = models.Kirli_Kiyafet(
            rfid_tag=kiyafet.rfid_tag,
            sicil_numarasi=kiyafet.sicil_numarasi,
            zaman_damgasi=now_utc
        )
        repository.add_islem(db, yeni)
        eklenenler.append({
            "islem_id": yeni.islem_id,
            "rfid_tag": kiyafet.rfid_tag,
            "sicil_numarasi": kiyafet.sicil_numarasi,
            "ad_soyad": f"{calisan.ad} {calisan.soyad}",
            "cinsiyet": calisan.cinsiyet,
            "zaman_damgasi": now_utc.isoformat()
        })

    repository.commit_db(db)
    write_audit_log(
        db=db, action="KIRLI_GIRIS", username=current_user.username,
        detail=f"RFID Oku: {len(eklenenler)} kıyafet kirli sepetine eklendi", ip_address=ip, status="success"
    )

    kalan = len(aday_kayitlar) - len(secilen)
    return {"durum": "ok", "eklenenler": eklenenler, "kalan_aday": kalan}

def process_islem(db: Session, request: Request, req: schemas.IslemRequest, current_user: models.User):
    rfid_tag = req.rfid_tag
    ip = get_client_ip(request)
    now_utc = datetime.now(timezone.utc)
    
    if req.islem_tipi == 'kirli':
        kiyafet = repository.get_kiyafet_by_rfid(db, rfid_tag)
        if not kiyafet:
            raise NotFoundException("Kıyafet", "Bu RFID tag sisteme kayıtlı değil.")
        yeni_islem = models.Kirli_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=kiyafet.sicil_numarasi, zaman_damgasi=now_utc)
        action_log = "KIRLI_GIRIS"
    elif req.islem_tipi == 'temiz':
        calisan = repository.get_calisan_by_sicil(db, req.sicil_numarasi)
        cinsiyet = calisan.cinsiyet if calisan else None
        raf_id = assign_shelf(db, cinsiyet=cinsiyet)
        if raf_id is None:
            raise BusinessLogicException("Tüm raflar dolu!")
        yeni_islem = models.Temiz_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=req.sicil_numarasi, zaman_damgasi=now_utc, raf_id=raf_id)
        action_log = "TEMIZ_GIRIS"
    elif req.islem_tipi == 'teslim':
        yeni_islem = models.Teslim_Edilen(rfid_tag=rfid_tag, sicil_numarasi=req.sicil_numarasi, zaman_damgasi=now_utc)
        action_log = "TESLIM_GIRIS"
    else:
        raise BusinessLogicException("Geçersiz işlem tipi")

    repository.add_islem(db, yeni_islem)
    repository.commit_db(db)
    db.refresh(yeni_islem)

    write_audit_log(
        db=db, action=action_log, username=current_user.username,
        detail=f"RFID: {rfid_tag} | Sicil: {yeni_islem.sicil_numarasi}", ip_address=ip, status="success"
    )
    return {"message": "İşlem başarılı", "islem_id": yeni_islem.islem_id}

def process_onay(db: Session, request: Request, req: schemas.IslemOnayRequest, current_user: models.User):
    kirli_kayit = repository.get_kirli_kayit_by_id(db, req.islem_id)
    if not kirli_kayit:
        raise NotFoundException("Kirli Kayıt")

    calisan = repository.get_calisan_by_sicil(db, kirli_kayit.sicil_numarasi)
    raf_id = assign_shelf(db, cinsiyet=calisan.cinsiyet if calisan else None)
    if raf_id is None:
        raise BusinessLogicException("Uygun raf bulunamadı!")
        
    yeni_temiz = models.Temiz_Kiyafet(
        rfid_tag=kirli_kayit.rfid_tag, sicil_numarasi=kirli_kayit.sicil_numarasi, 
        zaman_damgasi=datetime.now(timezone.utc), raf_id=raf_id
    )
    
    repository.add_islem(db, yeni_temiz)
    repository.delete_islem(db, kirli_kayit)
    repository.commit_db(db)

    write_audit_log(
        db=db, action="ISLEM_ONAYLA", username=current_user.username,
        detail=f"İşlem ID: {req.islem_id} | RFID: {kirli_kayit.rfid_tag} onaylandı (Temiz)",
        ip_address=get_client_ip(request), status="success"
    )
    return {"message": "Kıyafet temizlendi ve teslime hazır.", "yeni_islem_id": yeni_temiz.islem_id, "raf_id": yeni_temiz.raf_id}

def process_teslim(db: Session, request: Request, req: schemas.TeslimRequest, current_user: models.User):
    temiz_kayit = repository.get_temiz_kayit_by_id(db, req.islem_id)
    if not temiz_kayit:
        raise NotFoundException("Temiz Kayıt")
        
    if temiz_kayit.sicil_numarasi != req.sicil_numarasi:
        raise BusinessLogicException("Sicil numarası eşleşmiyor.")
        
    yeni_teslim = models.Teslim_Edilen(
        rfid_tag=temiz_kayit.rfid_tag, sicil_numarasi=temiz_kayit.sicil_numarasi, 
        zaman_damgasi=datetime.now(timezone.utc), raf_id=temiz_kayit.raf_id
    )
    
    repository.add_islem(db, yeni_teslim)
    repository.delete_islem(db, temiz_kayit)
    repository.commit_db(db)

    write_audit_log(
        db=db, action="TESLIM_GIRIS", username=current_user.username,
        detail=f"İşlem ID: {req.islem_id} | RFID: {temiz_kayit.rfid_tag} Teslim edildi",
        ip_address=get_client_ip(request), status="success"
    )
    return {"message": "Kıyafet başarıyla teslim edildi.", "yeni_islem_id": yeni_teslim.islem_id}

def get_stats(db: Session):
    bugun = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    kirli, temiz, teslim = repository.get_stats_counts(db, bugun)
    return schemas.StatsResponse(kirli_bugun=kirli, temiz_bugun=temiz, teslim_bugun=teslim)

def get_raf_stats(db: Session):
    occupancy = repository.get_raf_occupancy(db)
    occupancy_dict = {raf_id: count for raf_id, count in occupancy}
    result = {}
    for letter in RACK_LETTERS:
        rack_data = {}
        for floor in range(1, RACK_FLOORS + 1):
            cap = get_compartment_capacity(floor)
            for comp in range(1, RACK_COMPARTMENTS + 1):
                raf_id = f"{letter}{floor}{comp}"
                rack_data[raf_id] = {"count": occupancy_dict.get(raf_id, 0), "capacity": cap}
        result[letter] = rack_data
    return result

def get_raf_detail(db: Session, rack_letter: str):
    rack_letter = rack_letter.upper()
    if rack_letter not in RACK_LETTERS:
        raise BusinessLogicException("Geçersiz raf harfi.")
    items = repository.get_raf_items(db, rack_letter)
    compartments = {}
    for temiz, calisan in items:
        raf_id = temiz.raf_id
        if raf_id not in compartments: compartments[raf_id] = []
        compartments[raf_id].append({
            "rfid_tag": temiz.rfid_tag, "sicil_numarasi": temiz.sicil_numarasi,
            "ad_soyad": f"{calisan.ad} {calisan.soyad}" if calisan else "-",
            "zaman_damgasi": temiz.zaman_damgasi.isoformat() if temiz.zaman_damgasi else None
        })
    return compartments

def get_stats_history(db: Session, period: str):
    now = datetime.now(timezone.utc)
    days = 7 if period == "weekly" else 30
    start_date = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    kirli_records = repository.get_history_records(db, models.Kirli_Kiyafet, start_date)
    temiz_records = repository.get_history_records(db, models.Temiz_Kiyafet, start_date)
    teslim_records = repository.get_history_records(db, models.Teslim_Edilen, start_date)
    
    daily_stats = {f"{(start_date + timedelta(days=i)).day:02d}.{(start_date + timedelta(days=i)).month:02d}": {"kirli": 0, "temiz": 0, "teslim": 0} for i in range(days)}
    
    for rec in kirli_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats: daily_stats[dt_str]["kirli"] += 1
    for rec in temiz_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats: daily_stats[dt_str]["temiz"] += 1
    for rec in teslim_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats: daily_stats[dt_str]["teslim"] += 1

    return schemas.HistoryStatsResponse(
        labels=list(daily_stats.keys()),
        kirli_data=[d["kirli"] for d in daily_stats.values()],
        temiz_data=[d["temiz"] for d in daily_stats.values()],
        teslim_data=[d["teslim"] for d in daily_stats.values()]
    )

def get_tablo(db: Session, islem_tipi: str, q: Optional[str], limit: int, offset: int, current_user: models.User):
    if islem_tipi in ['teslim', 'kiyafet'] and current_user.role != 'admin':
        raise PermissionException("Sadece admin geçmiş kayıtları görebilir.")
        
    if islem_tipi in ('kirli', 'temiz', 'teslim'):
        model_map = {'kirli': models.Kirli_Kiyafet, 'temiz': models.Temiz_Kiyafet, 'teslim': models.Teslim_Edilen}
        model = model_map[islem_tipi]
        rows = repository.get_tablo_rows(db, model, limit)
        result = []
        for rec, calisan in rows:
            item = {"islem_id": rec.islem_id, "rfid_tag": rec.rfid_tag, "sicil_numarasi": rec.sicil_numarasi, "ad_soyad": f"{calisan.ad} {calisan.soyad}" if calisan else "-", "zaman_damgasi": rec.zaman_damgasi.isoformat() if rec.zaman_damgasi else None}
            if hasattr(rec, 'raf_id'): item["raf_id"] = rec.raf_id
            result.append(item)
        return result
    elif islem_tipi == 'kiyafet':
        total, rows = repository.get_kiyafet_rows(db, q, limit, offset)
        return {"total": total, "offset": offset, "limit": limit, "data": [{"rfid_tag": k.rfid_tag, "sicil_numarasi": k.sicil_numarasi, "ad_soyad": f"{c.ad} {c.soyad}" if c else "-"} for k, c in rows]}
    else:
        raise BusinessLogicException("Geçersiz işlem tipi")
