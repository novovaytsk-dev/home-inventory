import pytest
from httpx import AsyncClient

#  СПИСАНИЕ: НЕДОСТАТОЧНЫЙ ОСТАТОК 
@pytest.mark.asyncio
async def test_consume_insufficient_stock(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Молоко",
        "category": "dairy",
        "default_unit": "liter",
        "minimum_stock": 1
    }, headers=auth_headers)
    assert prod_res.status_code == 200
    product_id = prod_res.json()["id"]

    batch_res = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1.0,
        "purchased_at": "2026-07-25",
        "expires_at": "2026-08-05",
        "storage_location": "fridge",
        "price": 3.0
    }, headers=auth_headers)
    assert batch_res.status_code == 200

    response = await client.post(f"/products/{product_id}/consume", json={
        "quantity": 100.0,
        "strategy": "expires_first"
    }, headers=auth_headers)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INSUFFICIENT_STOCK"
    assert data["detail"]["details"]["requested"] == 100.0
    assert data["detail"]["details"]["available"] == 1.0

#  СПИСАНИЕ ИЗ НЕСКОЛЬКИХ ПАРТИЙ 
@pytest.mark.asyncio
async def test_consume_from_multiple_batches(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Йогурт",
        "category": "dairy",
        "default_unit": "piece",
        "minimum_stock": 2
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 2,
        "purchased_at": "2026-07-20",
        "expires_at": "2026-07-30",
        "storage_location": "fridge"
    }, headers=auth_headers)
    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 2,
        "purchased_at": "2026-07-22",
        "expires_at": "2026-08-02",
        "storage_location": "fridge"
    }, headers=auth_headers)

    consume_res = await client.post(f"/products/{product_id}/consume", json={
        "quantity": 3,
        "strategy": "expires_first"
    }, headers=auth_headers)
    assert consume_res.status_code == 200
    data = consume_res.json()
    assert data["consumed"] == 3
    used_batches = data["batches_used"]
    assert len(used_batches) == 2
    batches_res = await client.get(f"/products/{product_id}/batches", headers=auth_headers)
    batches = batches_res.json()
    remaining = sum(b["quantity_remaining"] for b in batches)
    assert remaining == 1  

#  СТРАТЕГИЯ EXPIRES_FIRST 
@pytest.mark.asyncio
async def test_consume_expires_first_strategy(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Молоко",
        "default_unit": "liter"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1,
        "expires_at": "2026-08-05",
        "storage_location": "fridge"
    }, headers=auth_headers)

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1,
        "expires_at": "2026-08-09",
        "storage_location": "fridge"
    }, headers=auth_headers)

    await client.post(f"/products/{product_id}/consume", json={
        "quantity": 1.0,
        "strategy": "expires_first"
    }, headers=auth_headers)

    batches_res = await client.get(f"/products/{product_id}/batches", headers=auth_headers)
    batches = batches_res.json()
    active = [b for b in batches if b["quantity_remaining"] > 0]
    assert len(active) == 1
    assert active[0]["expires_at"] == "2026-08-09T00:00:00" 

#  РУЧНОЙ ВЫБОР ПАРТИИ 
@pytest.mark.asyncio
async def test_consume_manual_batch_selection(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Сок",
        "default_unit": "liter"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    b1 = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1,
        "expires_at": "2026-08-01",
        "storage_location": "pantry"
    }, headers=auth_headers)
    b2 = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1,
        "expires_at": "2026-08-10",
        "storage_location": "pantry"
    }, headers=auth_headers)
    batch_id_2 = b2.json()["batch_id"]

    response = await client.post(f"/products/{product_id}/consume", json={
        "quantity": 0.5,
        "strategy": "manual",
        "manual_batch_id": batch_id_2
    }, headers=auth_headers)
    assert response.status_code == 200

    batches_res = await client.get(f"/products/{product_id}/batches", headers=auth_headers)
    batches = batches_res.json()
    for b in batches:
        if b["id"] == batch_id_2:
            assert b["quantity_remaining"] == 0.5
        else:
            assert b["quantity_remaining"] == 1.0

#  ЗАЩИТА ОТ ОТРИЦАТЕЛЬНОГО ОСТАТКА 
@pytest.mark.asyncio
async def test_consume_negative_quantity_rejected(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Хлеб",
        "default_unit": "piece"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]
    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1
    }, headers=auth_headers)

    response = await client.post(f"/products/{product_id}/consume", json={
        "quantity": -1,
        "strategy": "expires_first"
    }, headers=auth_headers)
    assert response.status_code == 422  
#  ВЫБРАСЫВАНИЕ ПАРТИИ 
@pytest.mark.asyncio
async def test_discard_batch(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Просроченное молоко",
        "default_unit": "liter"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    batch_res = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1,
        "expires_at": "2026-07-20" 
    }, headers=auth_headers)
    batch_id = batch_res.json()["batch_id"]

    discard_res = await client.post(f"/batches/{batch_id}/discard", json={
        "quantity": 0.5,
        "reason": "expired"
    }, headers=auth_headers)
    assert discard_res.status_code == 200
    data = discard_res.json()
    assert data["discarded"] == 0.5
    assert data["remaining"] == 0.5

#  ВЫБРАСЫВАНИЕ БОЛЬШЕ, ЧЕМ ОСТАЛОСЬ 
@pytest.mark.asyncio
async def test_discard_insufficient_quantity(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Кофе",
        "default_unit": "package"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]
    batch_res = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 1
    }, headers=auth_headers)
    batch_id = batch_res.json()["batch_id"]

    response = await client.post(f"/batches/{batch_id}/discard", json={
        "quantity": 10,
        "reason": "other"
    }, headers=auth_headers)
    assert response.status_code == 400

#  ИДЕМПОТЕНТНОСТЬ: ДОБАВЛЕНИЕ ПАРТИИ 
@pytest.mark.asyncio
async def test_idempotency_add_batch(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Рис",
        "default_unit": "kilogram"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    idem_key = "test-key-add-batch-1"
    payload = {
        "quantity": 2,
        "expires_at": "2026-12-31"
    }
    res1 = await client.post(
        f"/products/{product_id}/batches",
        json=payload,
        headers={**auth_headers, "Idempotency-Key": idem_key}
    )
    assert res1.status_code == 200
    batch_id = res1.json()["batch_id"]
    res2 = await client.post(
        f"/products/{product_id}/batches",
        json=payload,
        headers={**auth_headers, "Idempotency-Key": idem_key}
    )
    assert res2.status_code == 200
    assert res2.json()["batch_id"] == batch_id
    batches_res = await client.get(f"/products/{product_id}/batches", headers=auth_headers)
    batches = batches_res.json()
    assert len(batches) == 1
    assert batches[0]["quantity_initial"] == 2

#  ИДЕМПОТЕНТНОСТЬ: СПИСАНИЕ 
@pytest.mark.asyncio
async def test_idempotency_consume(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Макароны",
        "default_unit": "package"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 5
    }, headers=auth_headers)

    idem_key = "test-key-consume-1"
    payload = {"quantity": 2, "strategy": "expires_first"}
    res1 = await client.post(f"/products/{product_id}/consume", json=payload,
                             headers={**auth_headers, "Idempotency-Key": idem_key})
    assert res1.status_code == 200
    consumed1 = res1.json()["consumed"]

    res2 = await client.post(f"/products/{product_id}/consume", json=payload,
                             headers={**auth_headers, "Idempotency-Key": idem_key})
    assert res2.status_code == 200
    assert res2.json()["consumed"] == consumed1
    batches_res = await client.get(f"/products/{product_id}/batches", headers=auth_headers)
    remaining = sum(b["quantity_remaining"] for b in batches_res.json())
    assert remaining == 3  # 5 - 2

#  ИДЕМПОТЕНТНОСТЬ: ВЫБРАСЫВАНИЕ 
@pytest.mark.asyncio
async def test_idempotency_discard(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Чай",
        "default_unit": "package"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]
    batch_res = await client.post(f"/products/{product_id}/batches", json={
        "quantity": 10
    }, headers=auth_headers)
    batch_id = batch_res.json()["batch_id"]

    idem_key = "test-key-discard-1"
    discard_payload = {"quantity": 3, "reason": "expired"}
    res1 = await client.post(f"/batches/{batch_id}/discard", json=discard_payload,
                             headers={**auth_headers, "Idempotency-Key": idem_key})
    assert res1.status_code == 200
    rem1 = res1.json()["remaining"]

    res2 = await client.post(f"/batches/{batch_id}/discard", json=discard_payload,
                             headers={**auth_headers, "Idempotency-Key": idem_key})
    assert res2.status_code == 200
    assert res2.json()["remaining"] == rem1 

#  КОРРЕКТИРОВКА ОСТАТКА 
@pytest.mark.asyncio
async def test_adjust_stock(client: AsyncClient, auth_headers):
    prod_res = await client.post("/products", json={
        "name": "Сахар",
        "default_unit": "kilogram"
    }, headers=auth_headers)
    product_id = prod_res.json()["id"]

    await client.post(f"/products/{product_id}/batches", json={
        "quantity": 5
    }, headers=auth_headers)

    adjust_res = await client.post(f"/products/{product_id}/adjust", json={
        "actual_quantity": 3,
        "comment": "Пересчёт"
    }, headers=auth_headers)
    assert adjust_res.status_code == 200
    data = adjust_res.json()
    assert data["adjusted"] == -2

    ops_res = await client.get(f"/products/{product_id}/operations", headers=auth_headers)
    ops = ops_res.json()
    corrections = [op for op in ops if op["operation_type"] == "correction"]
    assert len(corrections) == 1
    assert corrections[0]["quantity"] == -2