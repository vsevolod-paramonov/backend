from fastapi import APIRouter, HTTPException
from models.schemas import PredictRequest, PredictResponse
from services.predict_service import predict_moderation
import logging

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
