from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.payment import PaymentResponse, PaymentCreate, PaymentAccepted
from app.services.payment import create_payment, get_payment
from app.utils.security import require_api_key

router = APIRouter(
    prefix="api/v1/payments", dependencies=[Depends(require_api_key)], tags=["payments"]
)


@router.get("/{payment_id}", status_code=status.HTTP_200_OK, response_model=PaymentResponse)
async def get_payment_by_id(payment_id: UUID, session: AsyncSession = Depends(get_db)):
    payment = await get_payment(session, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=PaymentAccepted)
async def create(
    data: PaymentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency key is required"
        )
    payment, _ = await create_payment(session, data, idempotency_key)
    return payment
