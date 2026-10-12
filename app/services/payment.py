from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.utils.enums import OutboxStatus, PaymentStatus


async def get_payment(session: AsyncSession, payment_id: int):
    return await session.get(Payment, payment_id)


async def create_payment(session: AsyncSession, data: PaymentCreate, idempotency_key: str):
    existing = await session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )

    if existing:
        return existing, False

    payment = Payment(
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        meta_data=data.meta_data,
        status=PaymentStatus.pending,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )
    session.add(payment)
    await session.flush()

    session.add(
        OutboxEvent(
            topic="payments.new",
            payload={"payment_id": str(payment.id)},
            status=OutboxStatus.pending,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(OutboxEvent).where(Payment.idempotency_key == idempotency_key)
        )
        if existing:
            return existing, False
        raise

    await session.refresh(payment)
    return payment, True
