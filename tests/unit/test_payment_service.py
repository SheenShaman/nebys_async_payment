from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.payment import PaymentStatus
from app.repositories.outbox import OutboxRepo
from app.repositories.payment import PaymentRepo
from app.services.payment import PaymentService


@pytest.fixture
def session():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def payment_data():
    return SimpleNamespace(
        amount="100.00",
        currency="RUB",
        description="Test payment",
        meta_data={"order_id": "order-123"},
        webhook_url="https://example.com/webhook",
    )


@pytest.fixture
def payment():
    return SimpleNamespace(
        id=123,
        amount="100.00",
        currency="RUB",
        status=PaymentStatus.pending,
        idempotency_key="idem-123",
    )


@pytest.mark.asyncio
async def test_create_payment_success(session, payment_data, payment, monkeypatch):
    """Новый платеж и Outbox-событие сохраняются одной транзакцией."""

    find_payment = AsyncMock(return_value=None)
    create_payment = AsyncMock(return_value=payment)
    create_outbox = AsyncMock()

    monkeypatch.setattr(PaymentRepo, "get_payment_by_idempotency_key", find_payment)
    monkeypatch.setattr(PaymentRepo, "create", create_payment)
    monkeypatch.setattr(OutboxRepo, "create", create_outbox)

    result, created = await PaymentService.create_payment(session, payment_data, "idem-123")

    assert result is payment
    assert created is True

    create_payment.assert_awaited_once()
    create_outbox.assert_awaited_once()

    assert create_outbox.await_args.kwargs["topic"] == "payments.new"
    assert create_outbox.await_args.kwargs["payload"] == {"payment_id": str(payment.id)}

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(payment)
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_payment_idempotency_key_exists(session, payment_data, payment, monkeypatch):
    """Повторный ключ возвращает существующий платеж."""

    find_payment = AsyncMock(return_value=payment)
    create_payment = AsyncMock()
    create_outbox = AsyncMock()

    monkeypatch.setattr(PaymentRepo, "get_payment_by_idempotency_key", find_payment)
    monkeypatch.setattr(PaymentRepo, "create", create_payment)
    monkeypatch.setattr(OutboxRepo, "create", create_outbox)

    result, created = await PaymentService.create_payment(session, payment_data, "idem-123")

    assert result is payment
    assert created is False

    create_payment.assert_not_awaited()
    create_outbox.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_payment_concurrent_idempotency_conflict(
    session, payment_data, payment, monkeypatch
):
    """
    Если параллельный запрос успел сохранить платеж,
    после IntegrityError сервис находит его и возвращает.
    """

    find_payment = AsyncMock(side_effect=[None, payment])
    create_payment = AsyncMock(return_value=payment)
    create_outbox = AsyncMock()

    session.commit.side_effect = IntegrityError(
        "INSERT INTO payments",
        {},
        Exception("unique constraint violation"),
    )

    monkeypatch.setattr(PaymentRepo, "get_payment_by_idempotency_key", find_payment)
    monkeypatch.setattr(PaymentRepo, "create", create_payment)
    monkeypatch.setattr(OutboxRepo, "create", create_outbox)

    result, created = await PaymentService.create_payment(session, payment_data, "idem-123")

    assert result is payment
    assert created is False

    session.rollback.assert_awaited_once()
    assert find_payment.await_count == 2


@pytest.mark.asyncio
async def test_create_payment_unrelated_integrity_error(session, payment_data, monkeypatch):
    """Если существующего платежа нет, ошибка не скрывается."""

    find_payment = AsyncMock(side_effect=[None, None])
    create_payment = AsyncMock(return_value=SimpleNamespace(id=123))
    create_outbox = AsyncMock()

    error = IntegrityError(
        "INSERT INTO payments",
        {},
        Exception("another integrity violation"),
    )
    session.commit.side_effect = error

    monkeypatch.setattr(PaymentRepo, "get_payment_by_idempotency_key", find_payment)
    monkeypatch.setattr(PaymentRepo, "create", create_payment)
    monkeypatch.setattr(OutboxRepo, "create", create_outbox)

    with pytest.raises(IntegrityError):
        await PaymentService.create_payment(session, payment_data, "idem-123")

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_payment_outbox_failure(session, payment_data, monkeypatch):
    """Ошибка создания Outbox не должна приводить к commit."""

    payment = SimpleNamespace(id=123)

    monkeypatch.setattr(
        PaymentRepo,
        "get_payment_by_idempotency_key",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(PaymentRepo, "create", AsyncMock(return_value=payment))

    monkeypatch.setattr(
        OutboxRepo,
        "create",
        AsyncMock(side_effect=RuntimeError("Outbox unavailable")),
    )

    with pytest.raises(RuntimeError, match="Outbox unavailable"):
        await PaymentService.create_payment(session, payment_data, "idem-123")

    session.commit.assert_not_awaited()
