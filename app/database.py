from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 'data' klasörünün varlığından emin oluyoruz ki SQLite dosyasını yazabilsin
os.makedirs("/code/data", exist_ok=True)

# SQLite tabanlı veritabanı sürücüsü adresi ("sqlite:///")
SQLALCHEMY_DATABASE_URL = "sqlite:////code/data/camasirhane.db"

# Eğer "/code" path'i (Yani Docker ortamı) yoksa (örneğin lokal geliştirme), ana dizine yaz
if not os.path.exists("/code"):
    SQLALCHEMY_DATABASE_URL = "sqlite:///./camasirhane.db"

# SQLite ile thread eşzamanlı çalışmasında sorun yaşanmaması için check_same_thread: False yapıldı
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
