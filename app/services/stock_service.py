import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.redis import redis_client
from app.models.product import Product
from app.models.batch import Batch
from app.models.operation import Operation

#  ДОБАВЛЕНИЕ ПАРТИИ 
async def add_batch_with_idempotency(
    product_id: int,
    batch_data: dict,
    idempotency_key: str | None,
    user_id: int,
    db: AsyncSession
):

    if idempotency_key:
        cached = await redis_client.get(f"idem:batch:{user_id}:{idempotency_key}")
        if cached:
            return json.loads(cached)

    batch = Batch(
        product_id=product_id,
        quantity_initial=batch_data["quantity"],
        quantity_remaining=batch_data["quantity"],
        purchased_at=batch_data.get("purchased_at", datetime.utcnow()),
        expires_at=batch_data.get("expires_at"),
        storage_location=batch_data.get("storage_location"),
        price=batch_data.get("price")
    )
    db.add(batch)
    await db.flush() 

    op = Operation(
        product_id=product_id,
        batch_id=batch.id,
        operation_type="purchase",
        quantity=batch.quantity_initial,
        comment=batch_data.get("comment"),
        idempotency_key=idempotency_key
    )
    db.add(op)

    await db.commit()
    await db.refresh(batch)

    result = {
        "batch_id": batch.id,
        "product_id": product_id,
        "quantity": batch.quantity_initial,
        "expires_at": batch.expires_at.isoformat() if batch.expires_at else None,
        "storage_location": batch.storage_location
    }

    if idempotency_key:
        await redis_client.setex(
            f"idem:batch:{user_id}:{idempotency_key}",
            86400,
            json.dumps(result, default=str)
        )
    return result

#  СПИСАНИЕ ТОВАРА 
async def consume_product_with_idempotency(
    product_id: int,
    quantity: float,
    strategy: str,
    manual_batch_id: int | None,
    comment: str | None,
    idempotency_key: str | None,
    user_id: int,
    db: AsyncSession
):

    if idempotency_key:
        cached = await redis_client.get(f"idem:consume:{user_id}:{idempotency_key}")
        if cached:
            return json.loads(cached)

    query = (
        select(Batch)
        .where(Batch.product_id == product_id, Batch.quantity_remaining > 0)
        .with_for_update()
    )
    if strategy == "expires_first":
        query = query.order_by(Batch.expires_at.asc().nulls_last())
    elif strategy == "oldest_first":
        query = query.order_by(Batch.purchased_at.asc())
    elif strategy == "manual" and manual_batch_id:
        query = select(Batch).where(Batch.id == manual_batch_id).with_for_update()
    else:
        raise HTTPException(400, detail="Invalid strategy")

    res = await db.execute(query)
    batches = res.scalars().all()

    total_available = sum(b.quantity_remaining for b in batches)
    if quantity > total_available:
        raise HTTPException(400, detail={
            "code": "INSUFFICIENT_STOCK",
            "message": "Недостаточно товара",
            "details": {"requested": quantity, "available": total_available}
        })

    remaining = quantity
    operations = []
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity_remaining, remaining)
        batch.quantity_remaining -= take
        operations.append(Operation(
            product_id=product_id,
            batch_id=batch.id,
            operation_type="consume",
            quantity=take,
            comment=comment or f"Списание по стратегии {strategy}",
            idempotency_key=idempotency_key
        ))
        remaining -= take

    db.add_all(operations)
    await db.commit()

    result = {
        "consumed": quantity,
        "batches_used": [
            {"batch_id": op.batch_id, "quantity": op.quantity}
            for op in operations
        ]
    }

    if idempotency_key:
        await redis_client.setex(
            f"idem:consume:{user_id}:{idempotency_key}",
            86400,
            json.dumps(result, default=str)
        )
    return result

#  ВЫБРАСЫВАНИЕ ПАРТИИ 
async def discard_batch_with_idempotency(
    batch_id: int,
    quantity: float,
    reason: str,
    idempotency_key: str | None,
    user_id: int,
    db: AsyncSession
):
    if idempotency_key:
        cached = await redis_client.get(f"idem:discard:{user_id}:{idempotency_key}")
        if cached:
            return json.loads(cached)

    batch = await db.get(Batch, batch_id, with_for_update=True)
    if not batch or batch.product.user_id != user_id:
        raise HTTPException(404, detail="Batch not found or access denied")
    if quantity > batch.quantity_remaining:
        raise HTTPException(400, detail="Quantity exceeds remaining")

    batch.quantity_remaining -= quantity
    op = Operation(
        product_id=batch.product_id,
        batch_id=batch.id,
        operation_type="discard",
        quantity=quantity,
        comment=f"Выброшено: {reason}",
        idempotency_key=idempotency_key
    )
    db.add(op)
    await db.commit()

    result = {"discarded": quantity, "batch_id": batch.id, "remaining": batch.quantity_remaining}
    if idempotency_key:
        await redis_client.setex(
            f"idem:discard:{user_id}:{idempotency_key}",
            86400,
            json.dumps(result, default=str)
        )
    return result

#  КОРРЕКТИРОВКА ОСТАТКА 
async def adjust_stock(
    product_id: int,
    actual_quantity: float,
    comment: str,
    user_id: int,
    db: AsyncSession
):
    batches = (await db.execute(
        select(Batch).where(Batch.product_id == product_id)
    )).scalars().all()
    current_stock = sum(b.quantity_remaining for b in batches)
    diff = actual_quantity - current_stock

    op = Operation(
        product_id=product_id,
        batch_id=None,
        operation_type="correction",
        quantity=diff,
        comment=comment,
        idempotency_key=None
    )
    db.add(op)
    await db.commit()
    return {"adjusted": diff, "new_total": actual_quantity}