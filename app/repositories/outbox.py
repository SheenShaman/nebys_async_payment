from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


class OutboxRepo:
    model = OutboxEvent

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs):
        outbox = OutboxEvent(**kwargs)
        session.add(outbox)
        await session.flush()
