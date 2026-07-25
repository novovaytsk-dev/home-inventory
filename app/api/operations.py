from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.operation import Operation
from app.models.batch import Batch
from app.api.dependencies import get_product_for_user
from app.schemas.operation import OperationOut

router = APIRouter(prefix="/products/{product_id}/operations", tags=["operations"])

@router.get("/", response_model=list[OperationOut])
async def get_operations(
    product_id: int,
    operation_type: Optional[str] = Query(None, description="purchase, consume, discard, correction, transfer"),
    date_from: Optional[datetime] = Query(None, description="Начальная дата в ISO формате"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата в ISO формате"),
    batch_id: Optional[int] = Query(None, description="Фильтр по конкретной партии"),
    storage_location: Optional[str] = Query(None, description="Фильтр по месту хранения партии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product: Product = Depends(get_product_for_user)
):
    """Возвращает историю операций для товара с возможностью фильтрации."""
    query = select(Operation).where(Operation.product_id == product_id)

    if operation_type:
        query = query.where(Operation.operation_type == operation_type)
    if batch_id:
        query = query.where(Operation.batch_id == batch_id)
    if date_from:
        query = query.where(Operation.created_at >= date_from)
    if date_to:
        query = query.where(Operation.created_at <= date_to)
    if storage_location:
        query = query.join(Batch, Operation.batch_id == Batch.id).where(
            Batch.storage_location == storage_location
        )

    query = query.order_by(Operation.created_at.desc())
    result = await db.execute(query)
    operations = result.scalars().all()
    return operations