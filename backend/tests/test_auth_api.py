import pytest

pytestmark = pytest.mark.asyncio


async def test_login_then_access_protected_route(client, test_user):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "testpassword123"},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == test_user.email
    token = body["access_token"]

    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == test_user.email


async def test_login_wrong_password_rejected(client, test_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_protected_route_without_token_rejected(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_protected_route_with_bad_token_rejected(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
