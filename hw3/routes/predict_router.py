from fastapi import APIRouter, HTTPException, Query
from models.schemas import PredictRequest, PredictResponse
from services.predict_service import predict_moderation, predict_from_db
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