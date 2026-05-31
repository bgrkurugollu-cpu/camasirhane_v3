from fastapi.testclient import TestClient

def test_rfid_oku_empty(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/islem/rfid-oku",
        headers={"Authorization": f"Bearer {admin_token}"}
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
