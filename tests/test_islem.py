from fastapi.testclient import TestClient

def test_rfid_oku_empty(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/islem/rfid-oku",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "durum" in data

def test_kirli_giris(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/islem",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_tipi": "kirli", "rfid_tag": "RFID-TEST"}
    )
    assert response.status_code == 200
    assert "islem_id" in response.json()
    islem_id = response.json()["islem_id"]
    
    # Clean it up via test_onay
    response_onay = client.post(
        "/api/v1/islem/onayla",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_id": islem_id}
    )
    assert response_onay.status_code == 200
    assert "yeni_islem_id" in response_onay.json()
    yeni_islem_id = response_onay.json()["yeni_islem_id"]
    
    # Teslim
    response_teslim = client.post(
        "/api/v1/islem/teslim",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_id": yeni_islem_id, "sicil_numarasi": "9999"}
    )
    assert response_teslim.status_code == 200

def test_shelf_allocation_gender(client: TestClient, admin_token: str):
    # Kadın çalışan kıyafeti kirliye ekle
    res_k = client.post(
        "/api/v1/islem",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_tipi": "kirli", "rfid_tag": "RFID-TEST-FEMALE"}
    )
    islem_id_k = res_k.json()["islem_id"]
    
    # Onayla -> Raf atanacak (Kadın olduğu için E ile başlamalı)
    res_k_onay = client.post(
        "/api/v1/islem/onayla",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_id": islem_id_k}
    )
    assert res_k_onay.status_code == 200
    raf_id_k = res_k_onay.json().get("raf_id", "")
    assert raf_id_k.startswith("E")

def test_rfid_mismatch(client: TestClient, admin_token: str):
    # Sicil numarasından farklı bir RFID ile teslim denemesi
    res = client.post(
        "/api/v1/islem/teslim",
        headers={"Authorization": f"Bearer {admin_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_id": 99999, "sicil_numarasi": "1111"} # Geçersiz ID ve Sicil
    )
    assert res.status_code != 200 # NotFound veya BadRequest dönmeli

def test_kirli_giris_admin_only(client: TestClient, user_token: str):
    # Kirli girişi yalnızca admin yetkisiyle yapılabilir; personel 403 almalı.
    res = client.post(
        "/api/v1/islem",
        headers={"Authorization": f"Bearer {user_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
        json={"islem_tipi": "kirli", "rfid_tag": "RFID-TEST"}
    )
    assert res.status_code == 403

def test_rfid_oku_admin_only(client: TestClient, user_token: str):
    # RFID Oku (kirli sepetine toplu ekleme) da admin'e özeldir.
    res = client.post(
        "/api/v1/islem/rfid-oku",
        headers={"Authorization": f"Bearer {user_token}", "x-csrf-token": "test"},
        cookies={"csrf_token": "test"},
    )
    assert res.status_code == 403
