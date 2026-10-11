from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.utils.enums import PaymentStatus


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
        status=PaymentStatus,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )
    session.add(payment)
    await session.flush()

    # Outbox pattern

    return payment, True
