from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification import Notification
from app.models.batch import Batch
from app.models.product import Product

async def create_notification_if_not_exists(
    db: AsyncSession,
    user_id: int,
    type: str,
    product_id: int,
    batch_id: int | None,
    message: str
) -> Notification | None:
    """
    Создаёт уведомление, если за сегодняшний день ещё нет такого же
    (по типу, продукту и партии) для этого пользователя.
    Возвращает созданное уведомление или None.
    """
    # Проверяем, нет ли уже уведомления за сегодня
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.product_id == product_id,
            Notification.batch_id == batch_id,
            Notification.created_at >= today_start
        )
    )
    if existing.scalar_one_or_none():
        return None

    notification = Notification(
        user_id=user_id,
        type=type,
        product_id=product_id,
        batch_id=batch_id,
        message=message
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification

async def get_unread_notifications(db: AsyncSession, user_id: int) -> list[Notification]:
    """Возвращает непрочитанные уведомления пользователя."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.read_at == None)
        .order_by(Notification.created_at.desc())
    )
    return result.scalars().all()

async def mark_notification_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    """Отмечает одно уведомление прочитанным. Возвращает True, если обновлено."""
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        return False
    notification.read_at = datetime.utcnow()
    await db.commit()
    return True

async def mark_all_notifications_read(db: AsyncSession, user_id: int) -> int:
    """Отмечает все уведомления пользователя прочитанными. Возвращает количество обновлённых."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.read_at == None
        )
    )
    notifications = result.scalars().all()
    count = len(notifications)
    for n in notifications:
        n.read_at = datetime.utcnow()
    await db.commit()
    return count