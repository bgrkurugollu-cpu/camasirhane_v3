"""Profil fotoğrafı yükleme güvenlik testleri.

Mimari Gate raporu BLOCKER 1'in (virus/malware tarama politikası) karşılığı:
MIME + boyut + magic-byte doğrulaması ve redde audit log yazımı doğrulanır.
"""
from fastapi.testclient import TestClient

from app.models import AuditLog

CSRF_HEADER = {"x-csrf-token": "test"}
CSRF_COOKIE = {"csrf_token": "test"}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VALID_PNG = PNG_SIGNATURE + b"\x00\x01\x02rest-of-png-bytes"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", **CSRF_HEADER}


def _upload(client, token, content: bytes, content_type: str = "image/png"):
    return client.post(
        "/api/v1/users/me/photo",
        files={"file": ("avatar.png", content, content_type)},
        headers=_auth(token), cookies=CSRF_COOKIE,
    )


def test_valid_png_accepted(client: TestClient, user_token: str):
    resp = _upload(client, user_token, VALID_PNG)
    assert resp.status_code == 200, resp.text
    assert resp.json()["profile_photo"].startswith("/static/avatars/avatar_")


def test_wrong_mime_rejected(client: TestClient, user_token: str):
    resp = _upload(client, user_token, VALID_PNG, content_type="image/jpeg")
    assert resp.status_code == 400


def test_empty_file_rejected(client: TestClient, user_token: str):
    resp = _upload(client, user_token, b"")
    assert resp.status_code == 400


def test_magic_byte_mismatch_rejected(client: TestClient, user_token: str):
    # MIME tipi image/png ama içerik PNG imzası taşımıyor (polyglot saldırısı taklidi)
    resp = _upload(client, user_token, b"GIF89a-not-a-png-payload")
    assert resp.status_code == 400


def test_oversized_png_rejected(client: TestClient, user_token: str):
    big = PNG_SIGNATURE + b"\x00" * (2 * 1024 * 1024 + 1)
    resp = _upload(client, user_token, big)
    assert resp.status_code == 400


def test_rejected_upload_is_audit_logged(client: TestClient, user_token: str, db_session):
    _upload(client, user_token, b"not-a-png", content_type="image/png")
    rejected = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "PHOTO_UPLOAD_REJECTED")
        .all()
    )
    assert len(rejected) >= 1
    assert rejected[-1].status == "failure"


def test_csrf_required_for_upload(client: TestClient, user_token: str):
    resp = client.post(
        "/api/v1/users/me/photo",
        files={"file": ("avatar.png", VALID_PNG, "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
