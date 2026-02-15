import json
import logging
from datetime import datetime
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"

_producer = None


async def get_producer():
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await _producer.start()
    return _producer


async def close_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def send_moderation_request(item_id):
    producer = await get_producer()
    message = {
        "item_id": item_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    await producer.send_and_wait(MODERATION_TOPIC, message)


async def send_to_dlq(original_message, error, retry_count=1):
    producer = await get_producer()
    dlq_message = {
        "original_message": original_message,
        "error": error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "retry_count": retry_count
    }
    await producer.send_and_wait(DLQ_TOPIC, dlq_message)

