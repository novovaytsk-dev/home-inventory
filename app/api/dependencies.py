from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.batch import Batch

async def get_product_for_user(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Product:
    """Получает продукт по ID с проверкой принадлежности пользователю."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == current_user.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "Товар не найден или доступ запрещён"}
        )
    return product

async def get_batch_for_user(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Batch:
    """Получает партию по ID с проверкой, что её продукт принадлежит пользователю."""
    result = await db.execute(
        select(Batch).join(Product).where(
            Batch.id == batch_id,
            Product.user_id == current_user.id
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BATCH_NOT_FOUND", "message": "Партия не найдена или доступ запрещён"}
        )
    return batch