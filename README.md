# Async Payment Service

Тестовое задание: асинхронный сервис обработки платежей.

## Стек

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 Async + PostgreSQL
- RabbitMQ + FastStream
- Alembic
- Docker Compose
- Outbox pattern
- Idempotency-Key
- Retry с exponential backoff
- Dead Letter Queue

## Архитектура

`POST /api/v1/payments` выполняет одну транзакцию PostgreSQL: создаёт `payments`
и `outbox`. После commit отдельный publisher читает pending-записи Outbox и
публикует `payments.new` в RabbitMQ. После подтверждения публикации запись
помечается `published`.

Consumer получает событие, эмулирует шлюз 2–5 секунд с вероятностью успеха 90%,
сохраняет результат и отправляет webhook. Ошибка webhook повторяется до 3 раз с
задержками 1 и 2 секунды. После третьей ошибки событие попадает в
`payments.dlq`.

Idempotency обеспечивается уникальным индексом PostgreSQL по `idempotency_key`:
повторный POST с тем же ключом возвращает существующий платёж и не создаёт новое
Outbox-событие.

## Запуск

```bash
cp .env .env
docker compose up --build
```

API: http://localhost:8000
RabbitMQ Management: http://localhost:15672 (`guest` / `guest`)

Swagger: http://localhost:8000/docs

## Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: dev-secret-api-key' \
  -H 'Idempotency-Key: order-123' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 1999.99,
    "currency": "RUB",
    "description": "Order #123",
    "metadata": {"order_id": "123"},
    "webhook_url": "https://example.com/webhook"
  }'
```

Ответ: `202 Accepted`.

## Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H 'X-API-Key: dev-secret-api-key'
```

## Webhook

После обработки сервис отправляет POST на `webhook_url`:

```json
{
  "payment_id": "uuid",
  "status": "succeeded",
  "amount": "1999.99",
  "currency": "RUB",
  "processed_at": "2026-10-05T12:00:00+00:00"
}
```

HTTP-коды 4xx/5xx, timeout и сетевые ошибки считаются ошибкой доставки.

## Гарантии

- API не публикует RabbitMQ-событие напрямую из HTTP transaction.
- Outbox обеспечивает eventual delivery после успешного commit.
- RabbitMQ durable queue/exchange и persistent messages используются для
  сохранности сообщений.
- Idempotency защищает от повторных запросов.
- Consumer имеет максимум 3 попытки.
- После окончательной ошибки сообщение записывается в DLQ.

## Структура

```text
app/
  api/             HTTP endpoints
  database/        SQLAlchemy setup
  messaging/       Outbox publisher
  models/          Payment/Outbox models
  schemas/         Pydantic DTOs
  services/        business logic
consumer/          RabbitMQ consumer
migrations/        Alembic migrations
```
