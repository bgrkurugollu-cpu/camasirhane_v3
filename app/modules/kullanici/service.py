import os, uuid
from sqlalchemy.orm import Session
from fastapi import Request
from ... import models, schemas, security
from ...utils import get_client_ip, write_audit_log
from ...exceptions import NotFoundException, BusinessLogicException, PermissionException
from . import repository

def update_user_me(db: Session, request: Request, data: schemas.UserProfileUpdate, current_user: models.User):
    if data.email is not None: current_user.email = data.email
    if data.phone is not None: current_user.phone = data.phone
    if data.title is not None: current_user.title = data.title
    if data.company is not None: current_user.company = data.company
    if data.password:
        current_user.hashed_password = security.get_password_hash(data.password)

    user = repository.update_user(db, current_user)
    write_audit_log(
        db=db, action="PROFILE_UPDATE", username=current_user.username,
        detail="Kendi profilini güncelledi", ip_address=get_client_ip(request), status="success"
    )
    return user

async def upload_profile_photo(db: Session, request: Request, contents: bytes, content_type: str, current_user: models.User):
    if content_type != "image/png":
        raise BusinessLogicException("Sadece .png formatında resim yükleyebilirsiniz.")
    
    if len(contents) > 2 * 1024 * 1024:
        raise BusinessLogicException("Dosya boyutu çok büyük! Maksimum 2MB yükleyebilirsiniz.")
    
    os.makedirs("app/static/avatars", exist_ok=True)
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.png"
    filepath = f"app/static/avatars/{filename}"
    
    with open(filepath, "wb") as f:
        f.write(contents)
        
    current_user.profile_photo = f"/static/avatars/{filename}"
    user = repository.update_user(db, current_user)
    return user

def get_all_users(db: Session, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler tüm kullanıcıları görebilir.")
    return repository.get_all_users(db)

def create_user_by_admin(db: Session, request: Request, data: schemas.UserCreate, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler yeni kullanıcı oluşturabilir.")
    
    existing_user = repository.get_user_by_username(db, data.username)
    if existing_user:
        raise BusinessLogicException("Bu kullanıcı adı zaten alınmış.")
        
    hashed_pwd = security.get_password_hash(data.password)
    new_user = models.User(
        username=data.username, hashed_password=hashed_pwd, role=data.role,
        title=data.title, company=data.company, email=data.email, phone=data.phone
    )
    user = repository.create_user(db, new_user)

    write_audit_log(
        db=db, action="USER_CREATE", username=current_user.username,
        detail=f"Yeni kullanıcı: {user.username}", ip_address=get_client_ip(request), status="success"
    )
    return user

def delete_user_by_admin(db: Session, request: Request, user_id: int, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler kullanıcı silebilir.")
        
    user = repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("Kullanıcı")
        
    if user.id == current_user.id:
        raise BusinessLogicException("Kendi kendinizi silemezsiniz.")

    deleted_username = user.username
    repository.delete_user(db, user)

    write_audit_log(
        db=db, action="USER_DELETE", username=current_user.username,
        detail=f"Silinen kullanıcı: {deleted_username}", ip_address=get_client_ip(request), status="success"
    )
    return {"message": "Kullanıcı başarıyla silindi."}

def update_user_by_admin(db: Session, request: Request, user_id: int, data: schemas.UserProfileUpdate, current_user: models.User):
    if current_user.role != "admin":
        raise PermissionException("Sadece adminler diğer kullanıcıları düzenleyebilir.")
        
    user = repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("Kullanıcı")
        
    if data.email is not None: user.email = data.email
    if data.phone is not None: user.phone = data.phone
    if data.title is not None: user.title = data.title
    if data.company is not None: user.company = data.company
    if data.password:
        user.hashed_password = security.get_password_hash(data.password)
        
    updated_user = repository.update_user(db, user)

    write_audit_log(
        db=db, action="USER_UPDATE", username=current_user.username,
        detail=f"Güncellenen kullanıcı: {updated_user.username}", ip_address=get_client_ip(request), status="success"
    )
    return updated_user
