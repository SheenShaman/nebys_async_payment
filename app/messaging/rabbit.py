from aio_pika import ExchangeType
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from app.database.config import get_settings

settings = get_settings()
broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)

payments_exchange = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
payments_new_queue = RabbitQueue("payments.new", durable=True)
payments_dlq = RabbitQueue("payments.dlq", durable=True)
