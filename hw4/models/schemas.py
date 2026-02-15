from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    seller_id: int = Field(..., ge=1)
    is_verified_seller: bool = Field(...)
    item_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int = Field(..., ge=1)
    images_qty: int = Field(..., ge=0)


class PredictResponse(BaseModel):
    is_violation: bool = Field(...)
    probability: float = Field(..., ge=0.0, le=1.0)


class AsyncPredictRequest(BaseModel):
    item_id: int = Field(..., ge=1)


class AsyncPredictResponse(BaseModel):
    task_id: int = Field(...)
    status: str = Field(...)
    message: str = Field(...)


class ModerationResultResponse(BaseModel):
    task_id: int = Field(...)
    status: str = Field(...)
    is_violation: Optional[bool] = Field(None)
    probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    error_message: Optional[str] = None

