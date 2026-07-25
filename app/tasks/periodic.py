from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.notification import Notification
from datetime import datetime, timedelta
import asyncio

@celery_app.task
def check_expirations_and_notify():
    async def _run():
        async with AsyncSessionLocal() as db:
            soon = datetime.utcnow() + timedelta(days=3) 
            expiring_batches = await db.execute(
                select(Batch).where(Batch.expires_at <= soon, Batch.quantity_remaining > 0)
            )
            for batch in expiring_batches.scalars():
                exists = await db.execute(
                    select(Notification).where(
                        Notification.batch_id == batch.id,
                        Notification.type == "expiring_soon",
                        Notification.created_at >= datetime.utcnow().date()
                    )
                )
                if not exists.scalar():
                    notif = Notification(
                        user_id=batch.product.user_id,
                        type="expiring_soon",
                        product_id=batch.product_id,
                        batch_id=batch.id,
                        message=f"Срок годности {batch.product.name} истекает {batch.expires_at.date()}"
                    )
                    db.add(notif)
            await db.commit()
    asyncio.run(_run())