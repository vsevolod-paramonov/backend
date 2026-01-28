import numpy as np
import logging
from models.schemas import PredictRequest, PredictResponse

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
    
    logger.info(f"Prediction: is_violation={is_violation}, probability={probability:.2f}")
    
    return PredictResponse(is_violation=is_violation, probability=probability)
