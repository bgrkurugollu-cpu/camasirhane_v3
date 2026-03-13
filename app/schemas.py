from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class IslemRequest(BaseModel):
    """
    Frontend'den yeni bir işlem kaydı oluşturulurken beklenen JSON şemasıdır.
    islem_tipi: 'kirli', 'temiz', veya 'teslim' olabilir.
    """
    islem_tipi: str
    rfid_tag: str
    sicil_numarasi: str

class IslemResponse(BaseModel):
    islem_id: int
    rfid_tag: Optional[str]
    sicil_numarasi: Optional[str]
    zaman_damgasi: datetime

class IslemOnayRequest(BaseModel):
    islem_id: int

class StatsResponse(BaseModel):
    """Ana ekrandaki istatistik grafikleri ve barları için dönen (Response) verilerin yapısıdır."""
    kirli_bugun: int
    temiz_bugun: int
    teslim_bugun: int

class DailyStat(BaseModel):
    tarih: str
    kirli: int
    temiz: int
    teslim: int

class HistoryStatsResponse(BaseModel):
    """Geçmişe dönük verilerin grafik oluşturabilmesi için 3 array ve 1 label listesi döner"""
    labels: list[str]
    kirli_data: list[int]
    temiz_data: list[int]
    teslim_data: list[int]

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    profile_photo: Optional[str] = None

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    password: Optional[str] = None

    class Config:
        from_attributes = True
