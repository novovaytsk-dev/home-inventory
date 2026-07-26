from fastapi import FastAPI
from app.api import auth, products, batches, operations

app = FastAPI(title="Home Inventory Manager")
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(batches.router)
app.include_router(operations.router)