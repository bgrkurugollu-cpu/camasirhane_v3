from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models, database

# Config
SECRET_KEY = "my-super-secret-laundry-key-for-mvp"  # MVP için statik
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 gün

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def verify_password(plain_password, hashed_password):
    """
    Kullanıcının girdiği düz metin şifre ile DB'deki hashli şifrenin eşleşip eşleşmediğini kontrol eder.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Yeni oluşturulan veya güncellenen şifreyi bcrypt ile hash'leyerek kaydeder."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Başarılı login sonrasında, kullanıcının bilgileri (data) ile süreli bir JWT token oluşturur.
    Bu token Client(App.js) tarafında localStorage'da saklanır ve sonraki isteklerde Header'da gönderilir.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    FastAPI Dependency Injection yordamıyla her API isteğinden önce çalışarak:
    1. Gelen Header'daki Token'ı çözer.
    2. Eğer çözemezse "Could not validate credentials" hatası verir (401).
    3. Token içindeki kullanıcı adını (sub) DB'de arar. Bulursa User objesini döner.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: models.User = Depends(get_current_user)):
    """
    Admin yetkisi gerektiren endpointlerin arasına giren ek güvenlik filtresidir.
    Kullanıcı admin değilse 403 Forbidden döner.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok.",
        )
    return current_user
