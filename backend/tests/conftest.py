"""
Fixtures for integration/API tests.

These tests require the docker-compose Postgres service running locally
(they exercise real SQLAlchemy models against a real DB, per the sprint's
verification checklist). Run `docker compose up -d postgres` first, then
`alembic upgrade head` against the test DB, then `pytest`.

Unit tests (test_security.py, test_mqtt_validation.py) do not need this
and will run without a DB.
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Device, User
from app.db.session import AsyncSessionLocal
from app.main import app


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        role="operator",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_device(db_session: AsyncSession) -> Device:
    device = Device(device_code=f"TEST-{uuid.uuid4().hex[:6]}", device_type="simulator", label="Test Device")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
