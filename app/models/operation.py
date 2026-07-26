from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    operation_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True, index=True)

    product = relationship("Product", back_populates="operations")
    batch = relationship("Batch", back_populates="operations")