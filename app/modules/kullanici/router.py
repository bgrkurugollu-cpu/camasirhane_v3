from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ... import models, schemas, database, security
from . import service

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(
    request: Request,
    data: schemas.UserProfileUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.update_user_me(db, request, data, current_user)

@router.post("/me/photo", response_model=schemas.UserResponse)
async def upload_profile_photo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    contents = await file.read()
    return await service.upload_profile_photo(db, request, contents, file.content_type, current_user)

@router.get("", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    return service.get_all_users(db, current_user)

@router.post("", response_model=schemas.UserResponse)
def create_user_by_admin(
    request: Request,
    data: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.create_user_by_admin(db, request, data, current_user)

@router.delete("/{user_id}")
def delete_user_by_admin(
    user_id: int, request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return service.delete_user_by_admin(db, request, user_id, current_user)

@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user_by_admin(
    user_id: int, request: Request, data: schemas.UserProfileUpdate,
    db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)
):
    return service.update_user_by_admin(db, request, user_id, data, current_user)
