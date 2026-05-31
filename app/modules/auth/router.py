from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ... import schemas, database
from . import service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    return service.process_login(db, request, response, form_data.username, form_data.password)

@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(database.get_db)):
    return service.process_refresh_token(db, request)

@router.post("/logout")
def logout(response: Response):
    return service.process_logout(response)
