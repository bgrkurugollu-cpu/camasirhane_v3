from sqlalchemy.orm import Session
from datetime import datetime
from ... import models

def get_user_by_username(db: Session, username: str) -> models.User:
    return db.query(models.User).filter(models.User.username == username).first()

def update_user(db: Session, user: models.User):
    db.commit()
    db.refresh(user)
    return user

def create_user(db: Session, user: models.User) -> models.User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
