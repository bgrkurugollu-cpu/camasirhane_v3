from datetime import datetime
import pyotp
from fastapi.testclient import TestClient

CSRF_HEADER = {"x-csrf-token": "test"}
CSRF_COOKIE = {"csrf_token": "test"}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", **CSRF_HEADER}


def _enable_mfa(client: TestClient, token: str) -> str:
    """Yardımcı: oturum açmış kullanıcı için MFA'yı etkinleştirir, secret'ı döner."""
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(token), cookies=CSRF_COOKIE)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")
    code = pyotp.TOTP(secret).now()
    activate = client.post("/api/v1/auth/mfa/activate", json={"code": code}, headers=_auth(token), cookies=CSRF_COOKIE)
    assert activate.status_code == 200, activate.text
    return secret


def test_login_success(client: TestClient):
    response = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_fail(client: TestClient):
    response = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "wrongpass"})
    assert response.status_code == 401

def test_access_protected_route_without_token(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

def test_access_protected_route_with_token(client: TestClient, admin_token: str):
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "testadmin"

def test_admin_route_as_user(client: TestClient, user_token: str):
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403

def test_account_lockout(client: TestClient):
    # Deney 1-5 hatalı
    for _ in range(5):
        client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "wrong"})
    
    # 6. deneme kilitli dönmeli (AuthException -> 401 veya benzeri, error json kontrolü)
    response = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "wrong"})
    assert response.status_code in [400, 401, 403]
    # Mesajda kilit veya benzeri bir hata kodu olmalı.
    json_resp = response.json()
    assert "error" in json_resp


# --- MFA (TOTP) — ADR 0007 ---

def test_mfa_setup_and_activate(client: TestClient, admin_token: str):
    secret = _enable_mfa(client, admin_token)
    assert secret  # base32 secret üretildi


def test_mfa_required_after_enable(client: TestClient, admin_token: str):
    _enable_mfa(client, admin_token)
    # MFA aktifken login artık access_token vermemeli; ikinci faktör istemeli
    resp = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("mfa_required") is True
    assert "mfa_token" in body
    assert "access_token" not in body


def test_mfa_verify_success(client: TestClient, admin_token: str):
    secret = _enable_mfa(client, admin_token)
    resp = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    mfa_token = resp.json()["mfa_token"]
    code = pyotp.TOTP(secret).now()
    verify = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert verify.status_code == 200, verify.text
    assert "access_token" in verify.json()


def test_mfa_verify_wrong_code(client: TestClient, admin_token: str):
    _enable_mfa(client, admin_token)
    resp = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    mfa_token = resp.json()["mfa_token"]
    # 2000 yılına ait kod bugün kesinlikle geçersizdir (deterministik yanlış kod)
    wrong = pyotp.TOTP("JBSWY3DPEHPK3PXP").at(datetime(2000, 1, 1))
    verify = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": wrong})
    assert verify.status_code == 401


def test_mfa_disable(client: TestClient, admin_token: str):
    secret = _enable_mfa(client, admin_token)
    code = pyotp.TOTP(secret).now()
    disable = client.post("/api/v1/auth/mfa/disable", json={"code": code}, headers=_auth(admin_token), cookies=CSRF_COOKIE)
    assert disable.status_code == 200, disable.text
    # Artık login doğrudan access_token vermeli
    resp = client.post("/api/v1/auth/token", data={"username": "testadmin", "password": "adminpass"})
    assert "access_token" in resp.json()


def test_mfa_setup_requires_csrf(client: TestClient, admin_token: str):
    # CSRF cookie/header olmadan MFA kurulumu (mutating) reddedilmeli
    resp = client.post("/api/v1/auth/mfa/setup", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403
