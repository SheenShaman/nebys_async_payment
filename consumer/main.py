import asyncio
import random
import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
from aio_pika import Message, connect_robust
from faststream import FastStream
from faststream.rabbit import (
    RabbitBroker,
    RabbitExchange,
    RabbitQueue,
)
from sqlalchemy import select

from app.models.payment import Payment
from app.utils.enums import PaymentStatus
from app.database.session import SessionLocal
from app.database.config import get_settings

settings = get_settings()
broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)
payment_exchange = RabbitExchange("payments", durable=True)
payments_queue = RabbitQueue("payments.new", durable=True)


async def send_webhook(payment: Payment) -> None:
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "amount": str(payment.amount),
        "currency": payment.currency.value,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }

    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.post(payment.webhook_url, json=payload)
        response.raise_for_status()


async def publish_to_dlq(raw_body: bytes, headers: dict) -> None:
    connection = await connect_robust(settings.RABBITMQ_URL)
    try:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await channel.declare_exchange("payments.dlq", "direct", durable=True)
        queue = await channel.declare_queue("payments.dlq", durable=True)
        await queue.bind(exchange, routing_key="payments.dlq")
        await exchange.publish(
            Message(
                raw_body,
                headers={**headers, "x-final-attempt": "true"},
                delivery_mode=2,
            ),
            routing_key="payments.dlq",
        )
    finally:
        await connection.close()


@broker.subscriber(payments_queue, exchange=payment_exchange)
async def process_payment(body: dict):
    payment_id = UUID(body["payment_id"])
    last_error = None

    for attempt in range(1, 4):
        try:
            async with SessionLocal() as session:
                payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
                if not payment:
                    return

                if payment.status == PaymentStatus.pending:
                    await asyncio.sleep(random.uniform(2, 5))
                    payment.status = (
                        PaymentStatus.succeeded if random.random() < 0.90 else PaymentStatus.failed
                    )
                    payment.processed_at = datetime.now(timezone.utc)
                    await session.commit()
                    await session.refresh(payment)

                await send_webhook(payment)
                return
        except Exception as e:
            last_error = e
            if attempt < 3:
                await asyncio.sleep(2 ** (attempt - 1))

    await publish_to_dlq(
        json.dumps({"payment_id": str(payment_id), "error": str(last_error)}).encode(),
        {"x-retry-count": "3"},
    )
