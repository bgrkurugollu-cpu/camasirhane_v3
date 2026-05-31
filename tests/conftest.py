import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.security import get_password_hash
from app.models import User, Calisan, Kiyafet

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test admin user
    if not db.query(User).filter(User.username == "testadmin").first():
        hashed_pw = get_password_hash("adminpass")
        admin = User(username="testadmin", hashed_password=hashed_pw, role="admin")
        db.add(admin)
        db.commit()
    
    # Create test worker and rfid
    if not db.query(Calisan).filter(Calisan.sicil_numarasi == "9999").first():
        calisan = Calisan(sicil_numarasi="9999", ad="Test", soyad="User", cinsiyet="Erkek")
        db.add(calisan)
        db.commit()
        
    if not db.query(Kiyafet).filter(Kiyafet.rfid_tag == "RFID-TEST").first():
        kiyafet = Kiyafet(rfid_tag="RFID-TEST", sicil_numarasi="9999")
        db.add(kiyafet)
        db.commit()
        
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
def client():
    return TestClient(app)

@pytest.fixture
def admin_token(client):
    response = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    return response.json()["access_token"]
