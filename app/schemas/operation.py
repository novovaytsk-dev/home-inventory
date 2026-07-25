from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class OperationOut(BaseModel):
    id: int
    product_id: int
    batch_id: Optional[int] = None
    operation_type: str
    quantity: float
    created_at: datetime
    comment: Optional[str] = None
    idempotency_key: Optional[str] = None

    class Config:
        from_attributes = True 