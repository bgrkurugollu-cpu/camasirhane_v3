from fastapi.testclient import TestClient

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
