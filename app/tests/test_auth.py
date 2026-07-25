import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "secret123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "secret123"
    })
    response = await client.post("/auth/login", data={
        "username": "user@example.com",
        "password": "secret123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "me@example.com",
        "password": "pass"
    })
    login_res = await client.post("/auth/login", data={
        "username": "me@example.com",
        "password": "pass"
    })
    token = login_res.json()["access_token"]

    response = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"

@pytest.mark.asyncio
async def test_unauthorized(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401