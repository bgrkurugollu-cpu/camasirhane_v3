from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ... import schemas, database, models, security
from . import service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/token")
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


# --- MFA (TOTP) — ADR 0007 ---

@router.post("/mfa/verify", response_model=schemas.Token)
def mfa_verify(
    request: Request,
    response: Response,
    body: schemas.MfaVerifyRequest,
    db: Session = Depends(database.get_db),
):
    """Login'in ikinci faktörü: mfa_token + TOTP kodu doğrulanır, oturum açılır."""
    return service.process_mfa_verify(db, request, response, body.mfa_token, body.code)

@router.post("/mfa/setup", response_model=schemas.MfaSetupResponse)
def mfa_setup(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Oturum açmış kullanıcı için MFA kaydını başlatır (secret + QR URI döner)."""
    return service.process_mfa_setup(db, request, current_user)

@router.post("/mfa/activate")
def mfa_activate(
    request: Request,
    body: schemas.MfaCodeRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Authenticator'dan alınan kod ile MFA'yı etkinleştirir."""
    return service.process_mfa_activate(db, request, current_user, body.code)

@router.post("/mfa/disable")
def mfa_disable(
    request: Request,
    body: schemas.MfaCodeRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Geçerli bir kod ile MFA'yı devre dışı bırakır."""
    return service.process_mfa_disable(db, request, current_user, body.code)
