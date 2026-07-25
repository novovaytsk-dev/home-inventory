class ShoppingListItem(Base):
    __tablename__ = "shopping_list"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # может быть null для ручного текста?
    recommended_quantity = Column(Float)
    reason = Column(String)
    priority = Column(String)  # high, medium, low
    added_automatically = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    purchased = Column(Boolean, default=False)