from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

def get_now():
    """UTC zaman diliminde şu anki zamanı döndürür."""
    return datetime.datetime.now(datetime.timezone.utc)

class AuditLog(Base):
    """
    Sistemdeki tüm kritik işlemlerin kim tarafından, ne zaman, hangi IP'den
    yapıldığını ve başarılı olup olmadığını kaydeden audit log tablosudur.
    """
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=get_now, index=True)
    username = Column(String, index=True, nullable=True)    # İşlemi yapan kullanıcı
    action = Column(String, index=True)                     # Olay tipi (LOGIN_SUCCESS, KIRLI_GIRIS, vb.)
    detail = Column(String, nullable=True)                  # Ek bilgi (RFID, sicil no, hedef kullanıcı)
    ip_address = Column(String, nullable=True)              # İstemci IP'si
    status = Column(String, default="success")              # 'success' veya 'fail'

class User(Base):
    """
    Sistemdeki kullanıcıları temsil eden veritabanı tablosudur.
    Rol tabanlı (admin, user) erişim kontrolü yapısı kurmak için kullanılır.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # 'admin' or 'user'
    
    # Profile fields
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)

    # Security fields
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # MFA (TOTP) — ADR 0007. mfa_enabled: 0/1 (SQLite uyumlu); mfa_secret: base32 TOTP secret
    mfa_enabled = Column(Integer, default=0)
    mfa_secret = Column(String, nullable=True)

class Calisan(Base):
    """
    Fabrikadaki veya tesisteki personeli (işçiyi) temsil eder.
    Sicil numarası benzersizdir (primary_key).
    """
    __tablename__ = "calisanlar"
    sicil_numarasi = Column(String, primary_key=True, index=True)
    ad = Column(String, index=True)
    soyad = Column(String, index=True)
    cinsiyet = Column(String, nullable=True)  # 'K' = Kadın, 'E' = Erkek

class Kiyafet(Base):
    """
    Personele zimmetlenmiş çamaşırları / üniformaları RFID tagi ile birbirine bağlar.
    """
    __tablename__ = "kiyafetler"
    rfid_tag = Column(String, primary_key=True, index=True)
    sicil_numarasi = Column(String, ForeignKey("calisanlar.sicil_numarasi"))

class Kirli_Kiyafet(Base):
    """
    O gün veya süreçte "Kirli" olarak sisteme okutulmuş ve onaya düşmüş işlemleri tutar.
    Kıyafet temizlendiğinde bu tablodan silinir ve Temiz/Teslim tablolarına aktarılır.
    """
    __tablename__ = "kirli_kiyafetler"
    islem_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rfid_tag = Column(String, index=True, nullable=True) # Hangi kıyafet
    sicil_numarasi = Column(String, index=True, nullable=True) # Kime ait
    zaman_damgasi = Column(DateTime(timezone=True), default=get_now)

class Temiz_Kiyafet(Base):
    __tablename__ = "temiz_kiyafetler"
    islem_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rfid_tag = Column(String, index=True, nullable=True)
    sicil_numarasi = Column(String, index=True, nullable=True)
    zaman_damgasi = Column(DateTime(timezone=True), default=get_now)
    raf_id = Column(String, nullable=True, index=True)  # Ör: A11, B35, H72

class Teslim_Edilen(Base):
    __tablename__ = "teslim_edilenler"
    islem_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rfid_tag = Column(String, index=True, nullable=True)
    sicil_numarasi = Column(String, index=True, nullable=True)
    zaman_damgasi = Column(DateTime(timezone=True), default=get_now)
    raf_id = Column(String, nullable=True, index=True)

class EdgeDevice(Base):
    """
    Fabrika ortamındaki Edge Sunucu cihazlarını temsil eder (bkz. Edge Gateway
    Network — docs/adr/0009). Cihaz kendini `enroll` ile tanıtır (public key gönderir),
    admin tarafından `approve` edilene kadar `pending` durumda bekler. Yalnızca
    `approved` cihaz veri (`ingest`) gönderebilir.
    """
    __tablename__ = "edge_devices"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_uid = Column(String, unique=True, index=True)   # Edge'in ürettiği UUID
    name = Column(String, nullable=True)                   # Kullanıcı dostu ad
    location = Column(String, nullable=True)               # Fabrika içi konum
    public_key = Column(Text, nullable=True)               # PEM (RS256) — cihaz JWT doğrulaması
    status = Column(String, default="pending", index=True) # pending | approved | revoked
    agent_version = Column(String, nullable=True)
    hardware = Column(Text, nullable=True)                  # JSON metni (okuyucu/yazıcı listesi)
    enrolled_at = Column(DateTime(timezone=True), default=get_now)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

class EdgeReadingReceipt(Base):
    """
    Edge'den gelen her okumanın `client_reading_id`'sini saklar; aynı okuma iki kez
    gönderilirse (retry) idempotent davranılır ve tekrar yazım yapılmaz.
    """
    __tablename__ = "edge_reading_receipts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_reading_id = Column(String, unique=True, index=True)
    device_id = Column(Integer, ForeignKey("edge_devices.id"), nullable=True, index=True)
    rfid_tag = Column(String, nullable=True)
    islem_id = Column(Integer, nullable=True)   # kirli_kiyafetler.islem_id
    status = Column(String, default="accepted") # accepted | rejected
    created_at = Column(DateTime(timezone=True), default=get_now)
