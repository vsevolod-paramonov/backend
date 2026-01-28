from pydantic import BaseModel, Field


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

