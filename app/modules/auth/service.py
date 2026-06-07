from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from fastapi import Request, Response
from ... import security
from ...utils import write_audit_log, get_client_ip
from ...exceptions import AuthException
from . import repository

def process_login(db: Session, request: Request, response: Response, username: str, password: str):
    ip = get_client_ip(request)
    now_utc = datetime.now(timezone.utc)
    
    user = repository.get_user_by_username(db, username)

    # SQLite, DateTime(timezone=True) alanlarını naive olarak geri döndürür;
    # PostgreSQL ise aware döndürür. İki ortamda da güvenli karşılaştırma için normalize edilir.
    locked_until = user.locked_until if user else None
    if locked_until is not None and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)

    if user and locked_until and locked_until > now_utc:
        raise AuthException("Çok fazla hatalı deneme. Hesabınız geçici olarak kilitlendi.", status_code=403)
        
    if not user or not security.verify_password(password, user.hashed_password):
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                user.locked_until = now_utc + timedelta(minutes=15)
            repository.update_user(db, user)
            
        write_audit_log(
            db=db, action="LOGIN_FAIL", username=username,
            detail="Hatalı kullanıcı adı veya şifre", ip_address=ip, status="fail"
        )
        raise AuthException("Kullanıcı adı veya şifre hatalı", status_code=401)
        
    user.failed_login_count = 0
    user.locked_until = None
    repository.update_user(db, user)

    # Birinci faktör (şifre) geçildi. MFA aktifse ikinci faktör (TOTP) istenir.
    if user.mfa_enabled:
        mfa_token = security.create_mfa_token(user.username)
        write_audit_log(
            db=db, action="LOGIN_MFA_CHALLENGE", username=user.username,
            detail="Şifre doğru; TOTP ikinci faktör bekleniyor", ip_address=ip, status="success"
        )
        return {"mfa_required": True, "mfa_token": mfa_token, "token_type": "mfa"}

    result = _issue_session(db, response, user, ip)
    # ADMIN_MFA_REQUIRED açıkken MFA tanımlamamış admin'e zorunlu kayıt uyarısı eklenir.
    if security.ADMIN_MFA_REQUIRED and user.role == "admin" and not user.mfa_enabled:
        result["mfa_enrollment_required"] = True
    return result


def _issue_session(db: Session, response: Response, user, ip: str):
    """Access token üretir, refresh token'ı httpOnly cookie olarak set eder ve
    LOGIN_SUCCESS audit kaydını yazar. Hem normal login hem MFA doğrulaması sonrası kullanılır."""
    access_token = security.create_access_token(data={"sub": user.username})
    refresh_token = security.create_refresh_token(data={"sub": user.username})

    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=True, samesite="lax", max_age=security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    write_audit_log(
        db=db, action="LOGIN_SUCCESS", username=user.username,
        detail=f"Rol: {user.role} | MFA: {'evet' if user.mfa_enabled else 'hayır'}",
        ip_address=ip, status="success"
    )
    return {"access_token": access_token, "token_type": "bearer"}


def process_mfa_verify(db: Session, request: Request, response: Response, mfa_token: str, code: str):
    """Login'in ikinci faktörü. mfa_token + TOTP kodu doğrulanırsa oturum açılır."""
    ip = get_client_ip(request)
    username = security.decode_mfa_token(mfa_token)
    if not username:
        raise AuthException("Geçersiz veya süresi dolmuş MFA oturumu", status_code=401)

    user = repository.get_user_by_username(db, username)
    if not user or not user.mfa_enabled or not user.mfa_secret:
        raise AuthException("MFA bu kullanıcı için aktif değil", status_code=400)

    if not security.verify_mfa_code(user.mfa_secret, code):
        write_audit_log(
            db=db, action="MFA_FAIL", username=username,
            detail="Geçersiz TOTP kodu", ip_address=ip, status="fail"
        )
        raise AuthException("Doğrulama kodu hatalı", status_code=401)

    write_audit_log(
        db=db, action="MFA_SUCCESS", username=username,
        detail="TOTP ikinci faktör doğrulandı", ip_address=ip, status="success"
    )
    return _issue_session(db, response, user, ip)


def process_mfa_setup(db: Session, request: Request, user):
    """Oturum açmış kullanıcı için MFA kaydını başlatır (secret üretir, henüz aktif etmez)."""
    if user.mfa_enabled:
        raise AuthException("MFA zaten aktif. Önce devre dışı bırakın.", status_code=400)

    secret = security.generate_mfa_secret()
    user.mfa_secret = secret
    user.mfa_enabled = 0
    repository.update_user(db, user)

    write_audit_log(
        db=db, action="MFA_SETUP_START", username=user.username,
        detail="Yeni TOTP secret üretildi", ip_address=get_client_ip(request), status="success"
    )
    return {"secret": secret, "otpauth_uri": security.mfa_provisioning_uri(secret, user.username)}


def process_mfa_activate(db: Session, request: Request, user, code: str):
    """Kayıt sırasında üretilen secret'a karşı kodu doğrulayıp MFA'yı etkinleştirir."""
    if not user.mfa_secret:
        raise AuthException("Önce MFA kurulumunu başlatın (/auth/mfa/setup).", status_code=400)
    if user.mfa_enabled:
        raise AuthException("MFA zaten aktif.", status_code=400)
    if not security.verify_mfa_code(user.mfa_secret, code):
        raise AuthException("Doğrulama kodu hatalı.", status_code=400)

    user.mfa_enabled = 1
    repository.update_user(db, user)
    write_audit_log(
        db=db, action="MFA_ENABLED", username=user.username,
        detail="Admin/kullanıcı MFA etkinleştirildi", ip_address=get_client_ip(request), status="success"
    )
    return {"message": "MFA başarıyla etkinleştirildi."}


def process_mfa_disable(db: Session, request: Request, user, code: str):
    """Geçerli bir TOTP kodu ile MFA'yı devre dışı bırakır ve secret'ı siler."""
    if not user.mfa_enabled:
        raise AuthException("MFA zaten devre dışı.", status_code=400)
    if not security.verify_mfa_code(user.mfa_secret, code):
        raise AuthException("Doğrulama kodu hatalı.", status_code=400)

    user.mfa_enabled = 0
    user.mfa_secret = None
    repository.update_user(db, user)
    write_audit_log(
        db=db, action="MFA_DISABLED", username=user.username,
        detail="MFA devre dışı bırakıldı", ip_address=get_client_ip(request), status="success"
    )
    return {"message": "MFA devre dışı bırakıldı."}

def process_refresh_token(db: Session, request: Request):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise AuthException("Refresh token bulunamadı")
        
    try:
        payload = security.jwt.decode(refresh_token_cookie, security.PUBLIC_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "refresh":
            raise AuthException("Geçersiz refresh token")
    except security.JWTError:
        raise AuthException("Geçersiz veya süresi dolmuş refresh token")
        
    user = repository.get_user_by_username(db, username)
    if not user:
        raise AuthException("Kullanıcı bulunamadı")
        
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

def process_logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Başarıyla çıkış yapıldı"}
