import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import AgencyUnit, User


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def operator_user(db_session: AsyncSession) -> User:
    email = f"op-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("oppassword123"),
        full_name="Operator User",
        role="operator",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_agency_unit_admin(client: AsyncClient, admin_user: User):
    token = create_access_token(str(admin_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit_code = f"POL-TEST-{uuid.uuid4().hex[:4]}"
    res = await client.post(
        "/api/v1/agency-units",
        json={"agency_type": "police", "unit_code": unit_code, "label": "Police Precinct 1", "current_latitude": 12.9716, "current_longitude": 77.5946},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["unit_code"] == unit_code
    assert data["agency_type"] == "police"
    assert data["label"] == "Police Precinct 1"
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_create_agency_unit_operator_forbidden(client: AsyncClient, operator_user: User):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/agency-units",
        json={"agency_type": "fire", "unit_code": f"FIRE-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_duplicate_agency_unit_code(client: AsyncClient, admin_user: User):
    token = create_access_token(str(admin_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    code = f"FIRE-{uuid.uuid4().hex[:4]}"
    await client.post("/api/v1/agency-units", json={"agency_type": "fire", "unit_code": code}, headers=headers)

    res = await client.post("/api/v1/agency-units", json={"agency_type": "fire", "unit_code": code}, headers=headers)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_filter_agency_units(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    u1 = AgencyUnit(agency_type="police", unit_code=f"P-{uuid.uuid4().hex[:4]}", status="available")
    u2 = AgencyUnit(agency_type="fire", unit_code=f"F-{uuid.uuid4().hex[:4]}", status="dispatched")
    db_session.add_all([u1, u2])
    await db_session.commit()

    res = await client.get("/api/v1/agency-units?agency_type=police", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert all(item["agency_type"] == "police" for item in data)

    res2 = await client.get("/api/v1/agency-units?status=dispatched", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert all(item["status"] == "dispatched" for item in data2)


@pytest.mark.asyncio
async def test_nearest_agency_units(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Bengaluru center
    base_lat, base_lng = 12.9716, 77.5946

    # Unit 1: ~1.1km away
    u1 = AgencyUnit(agency_type="fire", unit_code=f"NEAR-{uuid.uuid4().hex[:4]}", current_latitude=12.9800, current_longitude=77.5946, status="available")
    # Unit 2: ~11km away
    u2 = AgencyUnit(agency_type="fire", unit_code=f"FAR-{uuid.uuid4().hex[:4]}", current_latitude=13.0700, current_longitude=77.5946, status="available")
    db_session.add_all([u1, u2])
    await db_session.commit()

    res = await client.get(f"/api/v1/agency-units/nearest?agency_type=fire&lat={base_lat}&lng={base_lng}&limit=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    
    u1_item = next(item for item in data if item["unit_code"] == u1.unit_code)
    u2_item = next(item for item in data if item["unit_code"] == u2.unit_code)
    assert u1_item["distance_km"] < u2_item["distance_km"]



@pytest.mark.asyncio
async def test_get_agency_unit_by_id_and_code(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    code = f"POL-{uuid.uuid4().hex[:4]}"
    unit = AgencyUnit(agency_type="police", unit_code=code, status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    # By UUID
    res1 = await client.get(f"/api/v1/agency-units/{unit.id}", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["unit_code"] == code

    # By Code
    res2 = await client.get(f"/api/v1/agency-units/{code}", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["id"] == str(unit.id)

    # Unknown
    res3 = await client.get(f"/api/v1/agency-units/{uuid.uuid4()}", headers=headers)
    assert res3.status_code == 404
