from fastapi import FastAPI
from app.api import auth, products, batches
from app.api import operations

app.include_router(operations.router)
app = FastAPI(title="Home Inventory Manager")
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(batches.router)