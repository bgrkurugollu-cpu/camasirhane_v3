from sqlalchemy.orm import Session
from ... import models
from typing import List

def get_all_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()

def get_user_by_id(db: Session, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> models.User:
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: models.User) -> models.User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()

def update_user(db: Session, user: models.User) -> models.User:
    db.commit()
    db.refresh(user)
    return user
