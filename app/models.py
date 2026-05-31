from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
    profile_photo = Column(String, nullable=True)
    
    # Security fields
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

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
