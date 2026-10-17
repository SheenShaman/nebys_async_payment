from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.enums import OutboxStatus, PaymentStatus

from app.repositories.payment import PaymentRepo
from app.repositories.outbox import OutboxRepo


class PaymentService:
    @staticmethod
    async def get_payment(session: AsyncSession, payment_id: int) -> PaymentResponse | None:
        payment = await PaymentRepo.get_one_by_id(session, payment_id)
        if not payment:
            return None
        return payment

    @staticmethod
    async def create_payment(session: AsyncSession, data: PaymentCreate, idempotency_key: str):
        existing = await PaymentRepo.get_payment_by_idempotency_key(session, idempotency_key)

        if existing:
            return existing, False

        payment = await PaymentRepo.create(
            session,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            meta_data=data.meta_data,
            status=PaymentStatus.pending,
            idempotency_key=idempotency_key,
            webhook_url=str(data.webhook_url),
        )
        await OutboxRepo.create(
            session,
            topic="payments.new",
            payload={"payment_id": str(payment.id)},
            status=OutboxStatus.pending,
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await PaymentRepo.get_payment_by_idempotency_key(session, idempotency_key)
            if existing:
                return existing, False
            raise

        await session.refresh(payment)
        return payment, True
