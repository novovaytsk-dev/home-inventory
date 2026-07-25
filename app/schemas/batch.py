from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class BatchCreate(BaseModel):
    quantity: float = Field(..., gt=0)
    purchased_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    storage_location: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    comment: Optional[str] = None

class BatchOut(BaseModel):
    id: int
    product_id: int
    quantity_initial: float
    quantity_remaining: float
    purchased_at: Optional[datetime]
    expires_at: Optional[datetime]
    storage_location: Optional[str]
    price: Optional[float]

    class Config:
        from_attributes = True