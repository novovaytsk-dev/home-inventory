# Home Inventory Manager

## Запуск
1. Скопируйте .env.example -> .env и настройте переменные.
2. `docker-compose up -d`
3. Примените миграции: `docker-compose exec app alembic upgrade head`
4. API доступно на http://localhost:8000

## Модель данных
Описывает Product, Batch, Operation, ShoppingListItem, Notification...

## Алгоритм списания
Стратегия expires_first: сортировка партий по expires_at ASC, затем списание по очереди.

## Прогнозирование
Средний дневной расход за последние N дней. Дни без расхода учитываются как нулевой расход.

## Идемпотентность
Используется заголовок Idempotency-Key. Ключ сохраняется в Redis с TTL 24 часа.

## Конкурентный доступ
Используется SELECT FOR UPDATE при изменении партий, чтобы избежать двойного списания.

## Фоновые задачи
Celery Beat ежедневно проверяет сроки годности и создаёт уведомления, исключая дубликаты.