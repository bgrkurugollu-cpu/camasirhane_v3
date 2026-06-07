import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.security import get_password_hash
from app.models import User, Calisan, Kiyafet

import os

# Gerçek Postgres sağlanmışsa (ör. testcontainers veya CI'dan) onu kullan;
# aksi halde lokal hızlı çalışma için sqlite'a düş.
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed(db):
    """Testler için deterministik başlangıç verisini oluşturur.

    Cinsiyet kodlaması sistemin tek doğru kaynağı olan kısa kod ('K'/'E') ile
    tutulur (bkz. seed_1000.py ve shelf_service.assign_shelf).
    """
    hashed_pw = get_password_hash("adminpass")
    db.add(User(username="testadmin", hashed_password=hashed_pw, role="admin"))

    hashed_pw_user = get_password_hash("userpass")
    db.add(User(username="testuser", hashed_password=hashed_pw_user, role="user"))

    # Erkek çalışan + kıyafeti
    db.add(Calisan(sicil_numarasi="9999", ad="Test", soyad="User", cinsiyet="E"))
    db.add(Kiyafet(rfid_tag="RFID-TEST", sicil_numarasi="9999"))

    # Kadın çalışan + kıyafeti
    db.add(Calisan(sicil_numarasi="9998", ad="Ayse", soyad="Test", cinsiyet="K"))
    db.add(Kiyafet(rfid_tag="RFID-TEST-FEMALE", sicil_numarasi="9998"))

    db.commit()


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Her test fonksiyonu öncesi şemayı sıfırlar ve yeniden seed eder.

    Bu, testler arası izolasyonu garanti eder; örneğin hesap kilitleme testinin
    bıraktığı kilitli kullanıcı sonraki testleri etkilemez (implementation gate
    raporundaki test isolation bulgusunun karşılığı).
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        _seed(db)
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db_session():
    """Testlerin DB durumunu doğrudan inceleyebilmesi için ham bir session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    response = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    response = client.post("/api/v1/auth/token", data={"username": "testuser", "password": "userpass"})
    return response.json()["access_token"]
