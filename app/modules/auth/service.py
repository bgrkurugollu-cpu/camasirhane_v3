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
    
    if user and user.locked_until and user.locked_until > now_utc:
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
    
    access_token = security.create_access_token(data={"sub": user.username})
    refresh_token = security.create_refresh_token(data={"sub": user.username})
    
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=True, samesite="lax", max_age=security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    write_audit_log(
        db=db, action="LOGIN_SUCCESS", username=user.username,
        detail=f"Rol: {user.role}", ip_address=ip, status="success"
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
