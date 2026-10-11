import asyncio
import json
from datetime import datetime, timezone

from aio_pika import Message, connect_robust
from sqlalchemy import select

from app.database.config import get_settings
from app.database.session import SessionLocal
from app.models.outbox import OutboxEvent
from app.utils.enums import OutboxStatus

settings = get_settings()


async def publish_outbox():
    connection = await connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel(publisher_confirms=True)
    exchange = await channel.declare_exchange("payments", "direct", durable=True)
    queue = await channel.declare_queue("payments.new", durable=True)
    await queue.bind(exchange, routing_key="payments.new")
    dlq = await channel.declare_queue("payments.dlq", durable=True)

    try:
        while True:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(OutboxEvent)
                    .where(OutboxEvent.status == OutboxStatus.pending)
                    .order_by(OutboxEvent.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
                events = list(result.scalars())
                for event in events:
                    await exchange.publish(
                        Message(
                            json.dumps(event.payload).encode(),
                            content_type="application/json",
                            message_id=str(event.id),
                            delivery_mode=2,
                        ),
                        routing_key=event.topic,
                    )
                    event.status = OutboxStatus.published
                    event.published_at = datetime.now(timezone.utc)
                if events:
                    await session.commit()
            await asyncio.sleep(1)
    finally:
        await connection.close()
