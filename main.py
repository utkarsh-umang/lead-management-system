"""FastAPI application entry point."""

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import api_v1_router
from app.controllers.health import router as health_router
from app.core.config import config
from app.core.errors.exceptions import register_exception_handlers


def add_request_id_middleware(app: FastAPI) -> None:
    """Add request-ID middleware."""

    @app.middleware("http")
    async def _request_id(request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        return response

    return None  # type: ignore


app = FastAPI(
    title="enlead-be",
    version="0.1.0",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_request_id_middleware(app)
register_exception_handlers(app)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(api_v1_router, prefix=config.API_V1_STR)
