import asyncio

from app.messaging.publisher import publish_outbox
from consumer.main import app


async def main():
    await asyncio.gather(app.run(), publish_outbox())


if __name__ == "__main__":
    asyncio.run(main())
