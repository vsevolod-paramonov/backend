import json
import logging
import asyncio
from aiokafka import AIOKafkaConsumer

from database import get_db_pool, close_db_pool
from model import get_or_train_model
from repositories.item_repository import get_item_by_item_id
from app.repositories.moderation_repository import (
    get_pending_task_by_item_id, update_moderation_result
)
from app.clients.kafka import send_to_dlq
from services.predict_service import predict_moderation
from models.schemas import PredictRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
MODERATION_TOPIC = "moderation"
GROUP_ID = "moderation-worker-group"


async def process_moderation_message(message_data, model):
    item_id = message_data["item_id"]
    logger.info(f"Processing item_id={item_id}")
    
    try:
        item_data = await get_item_by_item_id(item_id)
        if not item_data:
            raise Exception(f"Item {item_id} not found")
        
        request = PredictRequest(
            seller_id=item_data["seller_id"],
            is_verified_seller=item_data["is_verified_seller"],
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            category=item_data["category"],
            images_qty=item_data["images_qty"]
        )
        result = predict_moderation(request, model)
        
        task_id = await get_pending_task_by_item_id(item_id)
        await update_moderation_result(
            task_id=task_id,
            status="completed",
            is_violation=result.is_violation,
            probability=result.probability
        )
        logger.info(f"Completed: item_id={item_id}, violation={result.is_violation}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error: {error_msg}")
        
        # Update status and send to DLQ
        task_id = await get_pending_task_by_item_id(item_id)
        if task_id:
            await update_moderation_result(
                task_id=task_id,
                status="failed",
                error_message=error_msg
            )
            await send_to_dlq(message_data, error_msg)


async def consume_messages():
    model = get_or_train_model()
    await get_db_pool()
    
    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    await consumer.start()
    logger.info(f"Worker started, consuming from {MODERATION_TOPIC}")
    
    try:
        async for message in consumer:
            await process_moderation_message(message.value, model)
    finally:
        await consumer.stop()
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(consume_messages())

