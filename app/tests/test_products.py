import pytest
from httpx import AsyncClient

@pytest.fixture
async def auth_headers(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "products@test.com",
        "password": "test"
    })
    login_res = await client.post("/auth/login", data={
        "username": "products@test.com",
        "password": "test"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers):
    response = await client.post("/products", json={
        "name": "Молоко",
        "category": "dairy",
        "default_unit": "liter",
        "minimum_stock": 1
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Молоко"
    assert data["current_stock"] == 0

@pytest.mark.asyncio
async def test_duplicate_product(client: AsyncClient, auth_headers):
    await client.post("/products", json={
        "name": "Хлеб",
        "category": "bakery",
        "default_unit": "piece",
        "minimum_stock": 2
    }, headers=auth_headers)
    response = await client.post("/products", json={
        "name": "Хлеб",
        "category": "bakery",
        "default_unit": "piece",
        "minimum_stock": 2
    }, headers=auth_headers)
    assert response.status_code in [400, 409] 

@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, auth_headers):
    await client.post("/products", json={
        "name": "Молоко",
        "category": "dairy",
        "default_unit": "liter",
        "minimum_stock": 1
    }, headers=auth_headers)
    await client.post("/products", json={
        "name": "Сыр",
        "category": "dairy",
        "default_unit": "gram",
        "minimum_stock": 200
    }, headers=auth_headers)
    response = await client.get("/products?category=dairy", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
