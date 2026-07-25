from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.operation import Operation
from app.models.batch import Batch
from app.models.product import Product

async def calculate_forecast(
    product_id: int,
    user_id: int,
    period_days: int,
    db: AsyncSession
) -> dict:
    """
    Прогнозирует, когда закончится товар.
    Возвращает словарь с прогнозом или признаком недостаточности данных.
    """
    product = await db.get(Product, product_id)
    if not product or product.user_id != user_id:
        return {
            "confidence": "insufficient_data",
            "estimated_depletion_date": None,
            "product_id": product_id,
            "current_stock": 0,
            "average_daily_consumption": 0,
            "estimated_days_remaining": None,
            "based_on_days": period_days
        }

    stock_query = select(func.sum(Batch.quantity_remaining)).where(
        Batch.product_id == product_id
    )
    stock_result = await db.execute(stock_query)
    current_stock = stock_result.scalar() or 0.0
    since = datetime.utcnow() - timedelta(days=period_days)
    consume_query = select(func.sum(Operation.quantity)).where(
        Operation.product_id == product_id,
        Operation.operation_type == "consume",
        Operation.created_at >= since
    )
    consume_result = await db.execute(consume_query)
    total_consumed = consume_result.scalar() or 0.0

    if total_consumed == 0 or period_days <= 0:
        return {
            "product_id": product_id,
            "current_stock": current_stock,
            "average_daily_consumption": 0.0,
            "estimated_days_remaining": None,
            "estimated_depletion_date": None,
            "confidence": "insufficient_data",
            "based_on_days": period_days
        }

    avg_daily = total_consumed / period_days

    if avg_daily > 0:
        days_remaining = current_stock / avg_daily
        est_date = datetime.utcnow().date() + timedelta(days=days_remaining)
    else:
        days_remaining = None
        est_date = None
    if period_days >= 7 and total_consumed > 0:
        confidence = "high"
    elif period_days >= 3 and total_consumed > 0:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "product_id": product_id,
        "current_stock": round(current_stock, 3),
        "average_daily_consumption": round(avg_daily, 3),
        "estimated_days_remaining": round(days_remaining, 1) if days_remaining is not None else None,
        "estimated_depletion_date": est_date.isoformat() if est_date else None,
        "confidence": confidence,
        "based_on_days": period_days
    }