import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import pyotp
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models, database

# Config – Faz 1 RS256 için private ve public key
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "certs/private_key.pem")
PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH", "certs/public_key.pem")

try:
    with open(PRIVATE_KEY_PATH, "r") as f:
        PRIVATE_KEY = f.read()
    with open(PUBLIC_KEY_PATH, "r") as f:
        PUBLIC_KEY = f.read()
except FileNotFoundError:
    # Test ortamları veya anahtar bulunamadığında hata fırlatmamak için fallback
    PRIVATE_KEY = "missing_key"
    PUBLIC_KEY = "missing_key"

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# MFA (TOTP) yapılandırması — ADR 0007
MFA_TOKEN_EXPIRE_MINUTES = int(os.getenv("MFA_TOKEN_EXPIRE_MINUTES", "5"))
MFA_ISSUER = os.getenv("MFA_ISSUER", "LaundroStar")
# True olduğunda, MFA tanımlamamış admin'ler login yanıtında zorunlu kayıt uyarısı alır.
ADMIN_MFA_REQUIRED = os.getenv("ADMIN_MFA_REQUIRED", "false").lower() in ("1", "true", "yes", "on")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

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
    Başarılı login sonrasında, kullanıcının bilgileri (data) ile süreli bir JWT access token oluşturur.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Refresh token oluşturur."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
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
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "access":
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


# ---------------------------------------------------------------------------
# MFA (TOTP) yardımcıları — ADR 0007: Admin İki Faktörlü Kimlik Doğrulama
# ---------------------------------------------------------------------------

def create_mfa_token(username: str) -> str:
    """Login'in birinci faktörü (şifre) geçildikten sonra, ikinci faktör (TOTP)
    adımını köprülemek için kullanılan kısa ömürlü ara token'ı üretir.

    Bu token access token DEĞİLDİR; yalnızca `type='mfa'` taşır ve sadece
    /auth/mfa/* uçlarında kabul edilir.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=MFA_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "type": "mfa", "exp": expire}
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)


def decode_mfa_token(token: str) -> Optional[str]:
    """MFA ara token'ını çözer; geçerli ve `type='mfa'` ise username döner, aksi halde None."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "mfa":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def generate_mfa_secret() -> str:
    """Kullanıcıya özel yeni bir base32 TOTP secret üretir."""
    return pyotp.random_base32()


def mfa_provisioning_uri(secret: str, username: str) -> str:
    """Authenticator uygulamalarının (Google/Microsoft Authenticator) okuyacağı
    otpauth:// URI'sini döner. QR koda çevrilerek kullanıcıya gösterilir."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=MFA_ISSUER)


def verify_mfa_code(secret: Optional[str], code: Optional[str]) -> bool:
    """Verilen 6 haneli TOTP kodunu secret'a karşı doğrular.
    Saat kayması toleransı için valid_window=1 (±30 sn) uygulanır."""
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1)
    except Exception:
        return False
