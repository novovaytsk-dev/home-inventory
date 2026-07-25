from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class UnitEnum(str, Enum):
    piece = "piece"
    gram = "gram"
    kilogram = "kilogram"
    milliliter = "milliliter"
    liter = "liter"
    package = "package"

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: Optional[str] = None
    default_unit: UnitEnum
    minimum_stock: float = Field(0, ge=0)

class ProductOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    default_unit: UnitEnum
    minimum_stock: float
    current_stock: float = 0  # будем вычислять динамически

    class Config:
        from_attributes = True