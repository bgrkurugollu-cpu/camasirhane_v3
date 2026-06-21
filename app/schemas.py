from pydantic import BaseModel, field_validator
import re
from datetime import datetime
from typing import Optional

class KiyafetCreate(BaseModel):
    rfid_tag: str
    sicil_numarasi: str
    ad: Optional[str] = None
    soyad: Optional[str] = None
    cinsiyet: Optional[str] = None

class KiyafetResponse(BaseModel):
    rfid_tag: str
    sicil_numarasi: str

    class Config:
        from_attributes = True

class TeslimRequest(BaseModel):
    islem_id: int
    sicil_numarasi: str

class IslemRequest(BaseModel):
    """
    Frontend'den yeni bir işlem kaydı oluşturulurken beklenen JSON şemasıdır.
    islem_tipi: 'kirli', 'temiz', veya 'teslim' olabilir.
    """
    islem_tipi: str
    rfid_tag: str
    sicil_numarasi: Optional[str] = None

class IslemResponse(BaseModel):
    islem_id: int
    rfid_tag: Optional[str]
    sicil_numarasi: Optional[str]
    zaman_damgasi: datetime
    raf_id: Optional[int] = None

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


class MfaVerifyRequest(BaseModel):
    """Login'in ikinci faktörü: şifre adımından dönen mfa_token + authenticator kodu."""
    mfa_token: str
    code: str


class MfaCodeRequest(BaseModel):
    """Oturum açmış kullanıcının MFA aktivasyon/iptal işlemleri için tek kod."""
    code: str


class MfaSetupResponse(BaseModel):
    """MFA kayıt başlangıcında dönen secret ve otpauth URI (QR için)."""
    secret: str
    otpauth_uri: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if not v:
            return v
        if len(v) < 12:
            raise ValueError("Şifre en az 12 karakter olmalıdır.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Şifre en az bir büyük harf içermelidir.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Şifre en az bir küçük harf içermelidir.")
        if not re.search(r"\d", v):
            raise ValueError("Şifre en az bir rakam içermelidir.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Şifre en az bir özel karakter içermelidir.")
        return v

class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    password: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if v is None:
            return v
        if len(v) < 12:
            raise ValueError("Şifre en az 12 karakter olmalıdır.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Şifre en az bir büyük harf içermelidir.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Şifre en az bir küçük harf içermelidir.")
        if not re.search(r"\d", v):
            raise ValueError("Şifre en az bir rakam içermelidir.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Şifre en az bir özel karakter içermelidir.")
        return v

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: Optional[str] = None
    action: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
