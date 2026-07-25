from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.product import Product
from app.models.batch import Batch
from app.models.operation import Operation
from app.services.forecast_service import calculate_forecast

async def generate_recommendations(db: AsyncSession, user_id: int) -> list[dict]:
    """
    Генерирует список рекомендаций для пользователя.
    Возвращает список словарей с полями type, priority, product_id, message и т.д.
    """
    recommendations = []

    expiring_threshold = datetime.utcnow() + timedelta(days=3) 
    expiring_batches = await db.execute(
        select(Batch, Product.name)
        .join(Product, Batch.product_id == Product.id)
        .where(
            Product.user_id == user_id,
            Batch.quantity_remaining > 0,
            Batch.expires_at != None,
            Batch.expires_at <= expiring_threshold,
            Batch.expires_at > datetime.utcnow()
        )
        .order_by(Batch.expires_at)
    )
    for batch, product_name in expiring_batches:
        days_left = (batch.expires_at - datetime.utcnow()).days
        recommendations.append({
            "type": "use_soon",
            "priority": "high" if days_left <= 1 else "medium",
            "product_id": batch.product_id,
            "batch_id": batch.id,
            "message": f"Используйте {product_name} в течение {days_left} дн.",
            "expires_at": batch.expires_at.isoformat()
        })

    products = await db.execute(
        select(Product).where(Product.user_id == user_id)
    )
    for product in products.scalars():
        stock_q = select(func.sum(Batch.quantity_remaining)).where(
            Batch.product_id == product.id, Batch.quantity_remaining > 0
        )
        current_stock = (await db.execute(stock_q)).scalar() or 0

        if current_stock < product.minimum_stock:
            recommendations.append({
                "type": "buy",
                "priority": "high" if current_stock == 0 else "medium",
                "product_id": product.id,
                "message": f"Товар {product.name} ниже минимального запаса",
                "recommended_quantity": product.minimum_stock - current_stock
            })
            continue 

        forecast = await calculate_forecast(product.id, user_id, 14, db)
        if forecast.get("estimated_days_remaining") is not None and forecast["estimated_days_remaining"] <= 3:
            recommendations.append({
                "type": "buy",
                "priority": "medium",
                "product_id": product.id,
                "message": f"{product.name} закончится примерно через {forecast['estimated_days_remaining']} дн.",
                "recommended_quantity": product.minimum_stock if product.minimum_stock > 0 else 1
            })

    days_since_last_op = 30  # порог
    for product in products.scalars():
        last_op = await db.execute(
            select(func.max(Operation.created_at)).where(Operation.product_id == product.id)
        )
        last_op_date = last_op.scalar()
        if last_op_date and (datetime.utcnow() - last_op_date).days > days_since_last_op:
            recommendations.append({
                "type": "check_stock",
                "priority": "low",
                "product_id": product.id,
                "message": f"Проверьте остаток {product.name}, давно не было операций"
            })

    for product in products.scalars():
        batches = await db.execute(
            select(Batch).where(
                Batch.product_id == product.id,
                Batch.quantity_remaining > 0,
                Batch.expires_at != None
            )
        )
        forecast = await calculate_forecast(product.id, user_id, 14, db)
        if forecast["confidence"] == "insufficient_data":
            continue
        avg_daily = forecast["average_daily_consumption"]
        for batch in batches.scalars():
            if batch.expires_at:
                days_until_expiry = (batch.expires_at - datetime.utcnow()).days
                if days_until_expiry <= 0:
                    continue 
                consumable_before_expiry = avg_daily * days_until_expiry
                if batch.quantity_remaining > consumable_before_expiry:
                    excess = batch.quantity_remaining - consumable_before_expiry
                    recommendations.append({
                        "type": "waste_risk",
                        "priority": "high" if days_until_expiry <= 3 else "medium",
                        "product_id": product.id,
                        "batch_id": batch.id,
                        "message": f"Риск не успеть использовать {product.name} (остаток {batch.quantity_remaining}, успеете ~{consumable_before_expiry:.1f})",
                        "expected_unused_quantity": round(excess, 2)
                    })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))
    return recommendations