"""API controllers (thin, delegate to services)."""

from fastapi import APIRouter

# Aggregate versioned routers here
api_v1_router = APIRouter()
# api_v1_router.include_router(items_router, prefix="/items", tags=["items"])
