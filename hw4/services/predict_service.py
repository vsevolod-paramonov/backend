import numpy as np
import logging
from fastapi import HTTPException
from models.schemas import PredictRequest, PredictResponse
from repositories.item_repository import get_item_by_item_id

logger = logging.getLogger(__name__)


def prepare_features(request: PredictRequest) -> np.ndarray:

    is_verified = 1 if request.is_verified_seller else 0
    images_qty_norm = request.images_qty / 10
    description_length_norm = len(request.description) / 1000
    category_norm = request.category / 100
    
    features = np.array([[is_verified, images_qty_norm, description_length_norm, category_norm]])
    return features


def predict_moderation(request: PredictRequest, model) -> PredictResponse:
    logger.info(
        f"Request: seller_id={request.seller_id}, item_id={request.item_id}, "
        f"is_verified_seller={request.is_verified_seller}, images_qty={request.images_qty}, "
        f"description_length={len(request.description)}, category={request.category}"
    )
    
    features = prepare_features(request)
    
    logger.info(f"Features preparing was done, features: {features[0].tolist()}")
    
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]
    
    is_violation = bool(prediction)
    
    logger.info(f"Prediction: is_violation={is_violation}, probability={probability:.4f}")
    
    return PredictResponse(is_violation=is_violation, probability=float(probability))


async def predict_from_db(item_id: int, model) -> PredictResponse:
    try:
        item_data = await get_item_by_item_id(item_id)
    except Exception as e:
        logger.error(f"Error getting item from DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if item_data is None:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")
    
    try:
        request = PredictRequest(
            seller_id=item_data["seller_id"],
            is_verified_seller=item_data["is_verified_seller"],
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            category=item_data["category"],
            images_qty=item_data["images_qty"]
        )
        
        return predict_moderation(request, model)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in predict_from_db: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")