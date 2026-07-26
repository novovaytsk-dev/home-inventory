from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.core.database import Base
import datetime

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) 
    product_id = Column(Integer, ForeignKey("products.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    read_at = Column(DateTime, nullable=True)