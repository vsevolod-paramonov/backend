from fastapi import APIRouter, HTTPException, Query, Path
from models.schemas import (
    PredictRequest, PredictResponse, 
    AsyncPredictRequest, AsyncPredictResponse,
    ModerationResultResponse
)
from services.predict_service import predict_moderation, predict_from_db
from app.repositories.moderation_repository import (
    create_moderation_task, get_moderation_task
)
from app.clients.kafka import send_moderation_request
from repositories.item_repository import get_item_by_item_id
import logging
import asyncpg

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    from main import app
    
    if app.state.model is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: Model is not loaded")
    
    try:
        result = predict_moderation(request, app.state.model)
        return result
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(item_id: int = Query(..., ge=1)) -> PredictResponse:
    from main import app
    
    if app.state.model is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: Model is not loaded")
    
    try:
        result = await predict_from_db(item_id, app.state.model)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during simple prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(request: AsyncPredictRequest) -> AsyncPredictResponse:
    """
    Create an async moderation task and send it to Kafka.
    """
    item_id = request.item_id
    
    # Check if advertisement exists
    try:
        item_data = await get_item_by_item_id(item_id)
        if item_data is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Advertisement with item_id={item_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking item existence: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )
    
    # Create moderation task
    try:
        task_id = await create_moderation_task(item_id)
    except Exception as e:
        logger.error(f"Error creating moderation task: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create moderation task: {str(e)}"
        )
    
    # Send message to Kafka
    try:
        await send_moderation_request(item_id)
    except Exception as e:
        logger.error(f"Error sending message to Kafka: {e}")
        # Note: Task is already created, but message wasn't sent
        # In production, you might want to handle this differently
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to send moderation request: {str(e)}"
        )
    
    return AsyncPredictResponse(
        task_id=task_id,
        status="pending",
        message="Moderation request accepted"
    )


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def get_moderation_result(
    task_id: int = Path(..., ge=1)
) -> ModerationResultResponse:
    """
    Get moderation result by task_id.
    """
    try:
        task = await get_moderation_task(task_id)
        if task is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task with id={task_id} not found"
            )
        
        return ModerationResultResponse(
            task_id=task["id"],
            status=task["status"],
            is_violation=task["is_violation"],
            probability=task["probability"],
            error_message=task["error_message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting moderation result: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )