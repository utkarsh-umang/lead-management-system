"""API controllers (thin, delegate to services)."""

from fastapi import APIRouter

from app.controllers.batches import router as batches_router
from app.controllers.enrichment import router as enrichment_router
from app.controllers.exports import router as exports_router
from app.controllers.leads import router as leads_router
from app.controllers.mapping_functions import router as mapping_functions_router
from app.controllers.sources import router as sources_router

# Aggregate versioned routers here
api_v1_router = APIRouter()
api_v1_router.include_router(batches_router, prefix="/batches", tags=["batches"])
api_v1_router.include_router(enrichment_router, prefix="/enrichment", tags=["enrichment"])
api_v1_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_v1_router.include_router(leads_router, prefix="/leads", tags=["leads"])
api_v1_router.include_router(
    mapping_functions_router, prefix="/mapping-functions", tags=["mapping-functions"]
)
api_v1_router.include_router(sources_router, prefix="/sources", tags=["sources"])
