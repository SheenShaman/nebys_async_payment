from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepo:
    model = Payment

    @classmethod
    async def get_one_by_id(cls, session: AsyncSession, payment_id: int) -> Payment | None:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_payment_by_idempotency_key(
        cls, session: AsyncSession, idempotency_key: str
    ) -> Payment | None:
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        session.add(payment)
        await session.flush()
        return payment
