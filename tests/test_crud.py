"""CRUD, istatistik ve yetkilendirme (RBAC) integration testleri.

Implementation gate raporundaki 'kritik iş akışı testleri eksik' ve
'admin-only endpoint yetki testleri eksik' bulgularını kapatır.
"""
from fastapi.testclient import TestClient

CSRF_HEADER = {"x-csrf-token": "test"}
CSRF_COOKIE = {"csrf_token": "test"}
STRONG_PW = "Str0ng!Pass123"


def _h(token: str, csrf: bool = False) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if csrf:
        headers.update(CSRF_HEADER)
    return headers


# ---------------- Kullanıcı yönetimi (Admin) ----------------

def test_admin_user_lifecycle(client: TestClient, admin_token: str):
    # Oluştur
    create = client.post(
        "/api/v1/users",
        json={"username": "yeni_op", "password": STRONG_PW, "role": "user"},
        headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert create.status_code == 200, create.text
    new_id = create.json()["id"]

    # Listele
    listing = client.get("/api/v1/users", headers=_h(admin_token))
    assert listing.status_code == 200
    assert any(u["username"] == "yeni_op" for u in listing.json())

    # Güncelle
    upd = client.put(
        f"/api/v1/users/{new_id}", json={"title": "Operatör"},
        headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Operatör"

    # Sil
    dele = client.delete(f"/api/v1/users/{new_id}", headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE)
    assert dele.status_code == 200


def test_create_user_weak_password_rejected(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/users", json={"username": "zayif", "password": "kisa", "role": "user"},
        headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert resp.status_code == 422


def test_user_cannot_create_user(client: TestClient, user_token: str):
    resp = client.post(
        "/api/v1/users", json={"username": "x", "password": STRONG_PW, "role": "user"},
        headers=_h(user_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert resp.status_code == 403


def test_profile_me_update(client: TestClient, user_token: str):
    me = client.get("/api/v1/users/me", headers=_h(user_token))
    assert me.status_code == 200
    upd = client.put(
        "/api/v1/users/me", json={"phone": "5551234567"},
        headers=_h(user_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert upd.status_code == 200
    assert upd.json()["phone"] == "5551234567"


# ---------------- Kıyafet / RFID (Admin) ----------------

def test_kiyafet_register_update_delete(client: TestClient, admin_token: str):
    reg = client.post(
        "/api/v1/kiyafet",
        json={"rfid_tag": "RFID-NEW", "sicil_numarasi": "7777", "ad": "Yeni", "soyad": "Personel", "cinsiyet": "E"},
        headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert reg.status_code == 200, reg.text

    upd = client.put(
        "/api/v1/kiyafet/RFID-NEW",
        json={"rfid_tag": "RFID-NEW2", "sicil_numarasi": "7777"},
        headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert upd.status_code == 200

    dele = client.delete("/api/v1/kiyafet/RFID-NEW2", headers=_h(admin_token, csrf=True), cookies=CSRF_COOKIE)
    assert dele.status_code == 200


def test_user_cannot_register_kiyafet(client: TestClient, user_token: str):
    resp = client.post(
        "/api/v1/kiyafet", json={"rfid_tag": "X", "sicil_numarasi": "1", "ad": "a", "soyad": "b", "cinsiyet": "E"},
        headers=_h(user_token, csrf=True), cookies=CSRF_COOKIE,
    )
    assert resp.status_code == 403


# ---------------- Çalışan ----------------

def test_get_calisan(client: TestClient, admin_token: str):
    resp = client.get("/api/v1/calisan/9999", headers=_h(admin_token))
    assert resp.status_code == 200
    assert resp.json()["cinsiyet"] == "E"


def test_get_calisan_not_found(client: TestClient, admin_token: str):
    resp = client.get("/api/v1/calisan/0000", headers=_h(admin_token))
    assert resp.status_code == 404


# ---------------- İstatistik / Raf ----------------

def test_stats_endpoints(client: TestClient, admin_token: str):
    assert client.get("/api/v1/stats", headers=_h(admin_token)).status_code == 200
    assert client.get("/api/v1/stats/raflar", headers=_h(admin_token)).status_code == 200
    assert client.get("/api/v1/stats/raf-detay/E", headers=_h(admin_token)).status_code == 200
    assert client.get("/api/v1/stats/history?period=weekly", headers=_h(admin_token)).status_code == 200
    assert client.get("/api/v1/stats/history?period=monthly", headers=_h(admin_token)).status_code == 200


def test_raf_detail_invalid_letter(client: TestClient, admin_token: str):
    resp = client.get("/api/v1/stats/raf-detay/Z", headers=_h(admin_token))
    assert resp.status_code == 400


# ---------------- Tablolar (kısmen admin-only) ----------------

def test_tablo_kirli_temiz_as_user(client: TestClient, user_token: str):
    assert client.get("/api/v1/tablo/kirli", headers=_h(user_token)).status_code == 200
    assert client.get("/api/v1/tablo/temiz", headers=_h(user_token)).status_code == 200


def test_tablo_teslim_admin_only(client: TestClient, user_token: str, admin_token: str):
    # user erişemez
    assert client.get("/api/v1/tablo/teslim", headers=_h(user_token)).status_code == 403
    # admin erişebilir
    assert client.get("/api/v1/tablo/teslim", headers=_h(admin_token)).status_code == 200


def test_tablo_kiyafet_admin(client: TestClient, admin_token: str):
    resp = client.get("/api/v1/tablo/kiyafet?q=RFID", headers=_h(admin_token))
    assert resp.status_code == 200
    assert "total" in resp.json()


# ---------------- Audit (Admin) ----------------

def test_audit_logs_admin_only(client: TestClient, user_token: str, admin_token: str):
    assert client.get("/api/v1/audit-logs", headers=_h(user_token)).status_code == 403
    ok = client.get("/api/v1/audit-logs", headers=_h(admin_token))
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)


# ---------------- Güvenlik: CSRF & raf doluluk ----------------

def test_csrf_required_for_mutation(client: TestClient, admin_token: str):
    # CSRF token olmadan kıyafet ekleme reddedilmeli
    resp = client.post(
        "/api/v1/kiyafet",
        json={"rfid_tag": "Y", "sicil_numarasi": "9999", "ad": "a", "soyad": "b", "cinsiyet": "E"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
