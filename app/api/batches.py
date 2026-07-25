from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.batch import BatchCreate, BatchOut
from app.services.stock_service import (
    add_batch_with_idempotency,
    consume_product_with_idempotency,
    discard_batch_with_idempotency,
    adjust_stock
)

router = APIRouter()

#  ДОБАВЛЕНИЕ ПАРТИИ 
@router.post("/products/{product_id}/batches", response_model=dict)
async def create_batch(
    product_id: int,
    batch_in: BatchCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return await add_batch_with_idempotency(
        product_id=product_id,
        batch_data=batch_in.dict(),
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        db=db
    )

#  ПРОСМОТР ПАРТИЙ 
@router.get("/products/{product_id}/batches", response_model=list[BatchOut])
async def list_batches(product_id: int, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    from sqlalchemy import select
    from app.models.batch import Batch
    batches = await db.execute(
        select(Batch).where(Batch.product_id == product_id)
        .order_by(Batch.expires_at.asc().nulls_last())
    )
    return batches.scalars().all()

#  СПИСАНИЕ 
@router.post("/products/{product_id}/consume")
async def consume(
    product_id: int,
    quantity: float,
    strategy: str = "expires_first",
    manual_batch_id: int | None = None,
    comment: str | None = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await consume_product_with_idempotency(
        product_id, quantity, strategy, manual_batch_id, comment,
        idempotency_key, current_user.id, db
    )

#  ВЫБРАСЫВАНИЕ 
@router.post("/batches/{batch_id}/discard")
async def discard(
    batch_id: int,
    quantity: float,
    reason: str = "expired",
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await discard_batch_with_idempotency(
        batch_id, quantity, reason, idempotency_key, current_user.id, db
    )

#  КОРРЕКТИРОВКА 
@router.post("/products/{product_id}/adjust")
async def adjust(
    product_id: int,
    actual_quantity: float,
    comment: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await adjust_stock(product_id, actual_quantity, comment, current_user.id, db)