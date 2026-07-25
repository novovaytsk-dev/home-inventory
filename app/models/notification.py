class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)  # expiring_soon, expired, low_stock, depletion_forecast, waste_risk
    product_id = Column(Integer, ForeignKey("products.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    read_at = Column(DateTime, nullable=True)