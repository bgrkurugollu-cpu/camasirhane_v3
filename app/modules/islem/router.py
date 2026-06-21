from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from ... import models, schemas, database, security
from . import service

router = APIRouter(prefix="", tags=["Islem"])

@router.post("/islem/rfid-oku")
def rfid_oku(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.require_admin)
):
    return service.process_rfid_oku(db, request, current_user)

@router.post("/islem", response_model=dict)
def process_islem(
    request: Request,
    req: schemas.IslemRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.require_admin)
):
    return service.process_islem(db, request, req, current_user)

@router.post("/islem/onayla")
def onayla_islem(
    request: Request,
    req: schemas.IslemOnayRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.process_onay(db, request, req, current_user)

@router.post("/islem/teslim")
def teslim_et(
    request: Request,
    req: schemas.TeslimRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.process_teslim(db, request, req, current_user)

@router.get("/stats", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_stats(db)

@router.get("/stats/raflar", response_model=dict)
def get_raf_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_raf_stats(db)

@router.get("/stats/raf-detay/{rack_letter}")
def get_raf_detail(rack_letter: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_raf_detail(db, rack_letter)

@router.get("/stats/history", response_model=schemas.HistoryStatsResponse)
def get_stats_history(period: str = "weekly", db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_stats_history(db, period)

@router.get("/tablo/{islem_tipi}")
def get_tablo(islem_tipi: str, q: Optional[str] = None, limit: int = 50, offset: int = 0, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_tablo(db, islem_tipi, q, limit, offset, current_user)
