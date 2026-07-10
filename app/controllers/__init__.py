"""API controllers (thin, delegate to services)."""

from fastapi import APIRouter

from app.controllers.batches import router as batches_router

# Aggregate versioned routers here
api_v1_router = APIRouter()
api_v1_router.include_router(batches_router, prefix="/batches", tags=["batches"])
