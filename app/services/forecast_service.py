from datetime import datetime, timedelta

async def calculate_forecast(product_id: int, user_id: int, period_days: int = 14, db: AsyncSession):
    since = datetime.utcnow() - timedelta(days=period_days)
    query = select(func.sum(Operation.quantity)).where(
        Operation.product_id == product_id,
        Operation.operation_type == "consume",
        Operation.created_at >= since
    )
    total_consumed = (await db.execute(query)).scalar() or 0
    if total_consumed == 0:
        return {"confidence": "insufficient_data", "estimated_depletion_date": None, ...}
    avg_daily = total_consumed / period_days
    stock = await get_current_stock(product_id, db)
    if avg_daily == 0:
        days_remaining = None
    else:
        days_remaining = stock / avg_daily
    est_date = datetime.utcnow().date() + timedelta(days=days_remaining) if days_remaining else None
    confidence = "high" if total_consumed > 0 and period_days >= 7 else "medium"
    return {
        "product_id": product_id,
        "current_stock": stock,
        "average_daily_consumption": round(avg_daily, 3),
        "estimated_days_remaining": round(days_remaining, 1) if days_remaining else None,
        "estimated_depletion_date": est_date.isoformat() if est_date else None,
        "confidence": confidence,
        "based_on_days": period_days
    }