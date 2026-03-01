import json
import hashlib
from app.clients.redis_client import get_redis
from models.schemas import PredictResponse, ModerationResultResponse

# TTL 1 час
TTL = 3600
PREDICTION_CACHE_TTL_SEC = TTL


def _key_req(data):
    return "prediction:req:" + hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _key_item(item_id):
    return f"prediction:item:{item_id}"


def _key_task(task_id):
    return f"moderation:task:{task_id}"


async def get_cached_prediction_by_request(request_data: dict):
    r = await get_redis()
    raw = await r.get(_key_req(request_data))
    return PredictResponse(**json.loads(raw)) if raw else None


async def set_cached_prediction_by_request(request_data: dict, result: PredictResponse):
    await (await get_redis()).setex(_key_req(request_data), TTL, result.model_dump_json())


async def get_cached_prediction_by_item(item_id: int):
    r = await get_redis()
    raw = await r.get(_key_item(item_id))
    return PredictResponse(**json.loads(raw)) if raw else None


async def set_cached_prediction_by_item(item_id: int, result: PredictResponse):
    await (await get_redis()).setex(_key_item(item_id), TTL, result.model_dump_json())


async def get_cached_moderation_result(task_id: int):
    r = await get_redis()
    raw = await r.get(_key_task(task_id))
    return ModerationResultResponse(**json.loads(raw)) if raw else None


async def set_cached_moderation_result(task_id: int, result: ModerationResultResponse):
    await (await get_redis()).setex(_key_task(task_id), TTL, result.model_dump_json())


async def delete_cached_prediction_for_item(item_id: int):
    await (await get_redis()).delete(_key_item(item_id))
