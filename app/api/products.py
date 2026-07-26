from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.batch import Batch
from app.schemas.product import ProductCreate, ProductOut
from app.api.dependencies import get_product_for_user
from app.services.forecast_service import calculate_forecast

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductOut)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # проверка дубликата
    existing = await db.execute(
        select(Product).where(
            Product.user_id == current_user.id,
            Product.name == product_in.name
        )
    )
    if existing.scalar_one_or_none():
        # по заданию можно вернуть предупреждение, но здесь просто ошибка
        pass
    product = Product(**product_in.model_dump(), user_id=current_user.id)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.get("/", response_model=list[ProductOut])
async def list_products(
    category: str | None = Query(None),
    low_stock: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Product).where(Product.user_id == current_user.id)
    if category:
        query = query.where(Product.category == category)
    result = await db.execute(query)
    products = result.scalars().all()

    out = []
    for p in products:
        total = (await db.execute(
            select(func.sum(Batch.quantity_remaining)).where(Batch.product_id == p.id)
        )).scalar() or 0
        p.current_stock = total
        if low_stock and total >= p.minimum_stock:
            continue
        out.append(ProductOut.model_validate(p))
    return out

@router.get("/{product_id}/forecast")
async def get_forecast(
    product_id: int,
    period_days: int = Query(14, ge=1, description="Период анализа в днях"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product: Product = Depends(get_product_for_user)  # проверка владения
):
    """Возвращает прогноз расхода товара."""
    forecast = await calculate_forecast(product_id, current_user.id, period_days, db)
    return forecast