import pytest
from httpx import AsyncClient

@pytest.fixture
async def setup_forecast(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "forecast@test.com",
        "password": "test"
    })
    login_res = await client.post("/auth/login", data={
        "username": "forecast@test.com",
        "password": "test"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    prod_res = await client.post("/products", json={
        "name": "Молоко",
        "category": "dairy",
        "default_unit": "liter",
        "minimum_stock": 1
    }, headers=headers)
    product_id = prod_res.json()["id"]

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 5.0,
        "purchased_at": "2026-07-10",
        "expires_at": "2026-07-30",
        "storage_location": "fridge",
        "price": 3.0
    }, headers=headers)

    await client.post(f"/products/{product_id}/consume", json={
        "quantity": 2.0,
        "strategy": "expires_first"
    }, headers=headers)

    return headers, product_id

@pytest.mark.asyncio
async def test_forecast_sufficient_data(client: AsyncClient, setup_forecast):
    headers, product_id = setup_forecast
    response = await client.get(f"/products/{product_id}/forecast", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_stock"] == 3.0
    assert data["confidence"] != "insufficient_data"
    assert data["estimated_days_remaining"] is not None

@pytest.mark.asyncio
async def test_forecast_insufficient_data(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Сыр",
        "category": "dairy",
        "default_unit": "gram",
        "minimum_stock": 100
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]
    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 500,
        "storage_location": "fridge"
    }, headers=auth_headers)
    response = await client.get(f"/products/{product_id}/forecast", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] == "insufficient_data"
    assert data["estimated_depletion_date"] is None