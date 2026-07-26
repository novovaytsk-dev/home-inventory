import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers):
    response = await client.post("/products/", json={
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
    await client.post("/products/", json={
        "name": "Хлеб",
        "category": "bakery",
        "default_unit": "piece",
        "minimum_stock": 2
    }, headers=auth_headers)
    response = await client.post("/products/", json={
        "name": "Хлеб",
        "category": "bakery",
        "default_unit": "piece",
        "minimum_stock": 2
    }, headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, auth_headers):
    await client.post("/products/", json={
        "name": "Молоко",
        "category": "dairy",
        "default_unit": "liter",
        "minimum_stock": 1
    }, headers=auth_headers)
    await client.post("/products/", json={
        "name": "Сыр",
        "category": "dairy",
        "default_unit": "gram",
        "minimum_stock": 200
    }, headers=auth_headers)
    response = await client.get("/products/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2