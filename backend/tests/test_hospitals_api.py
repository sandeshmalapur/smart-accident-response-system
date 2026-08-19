import pytest
from app.db.models import Hospital
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_hospital_crud_and_nearest(client, test_user, db_session: AsyncSession):
    # Set admin role for test user to allow POST /hospitals
    test_user.role = "admin"
    await db_session.commit()

    # 1. Login to get token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "testpassword123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register Hospitals via POST /hospitals
    hosp1_payload = {
        "name": "Central General Hospital",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "phone": "+91 80 1111 2222",
    }
    hosp2_payload = {
        "name": "Eastside Medical Center",
        "latitude": 13.0000,
        "longitude": 77.6500,
        "phone": "+91 80 3333 4444",
    }

    res1 = await client.post("/api/v1/hospitals", json=hosp1_payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["name"] == "Central General Hospital"

    res2 = await client.post("/api/v1/hospitals", json=hosp2_payload, headers=headers)
    assert res2.status_code == 201

    # 3. List hospitals via GET /hospitals
    list_res = await client.get("/api/v1/hospitals", headers=headers)
    assert list_res.status_code == 200
    hospitals_list = list_res.json()
    assert len(hospitals_list) >= 2

    # 4. Get nearest hospitals from point close to Central General (12.9720, 77.5950)
    nearest_res = await client.get("/api/v1/hospitals/nearest?lat=12.9720&lng=77.5950&limit=2", headers=headers)
    assert nearest_res.status_code == 200
    nearest_list = nearest_res.json()
    assert len(nearest_list) >= 1
    assert nearest_list[0]["name"] == "Central General Hospital"
    assert "distance_km" in nearest_list[0]
