"""Custom HTTP exceptions and global handlers."""

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class APIError(BaseModel):
    """Consistent error response schema."""

    error_code: str
    message: str
    details: dict | None = None


class NotFoundError(HTTPException):
    """404 - Resource not found."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            status_code=404,
            detail={"error_code": "NOT_FOUND", "message": f"{resource} {resource_id} not found"},
        )


class ValidationError(HTTPException):
    """422 - Validation error."""

    def __init__(self, detail: str | dict) -> None:
        if isinstance(detail, str):
            detail = {"error_code": "VALIDATION_ERROR", "message": detail}
        super().__init__(status_code=422, detail=detail)


def _format_http_exception(exc: HTTPException) -> dict:
    detail = exc.detail
    if isinstance(detail, dict):
        return {
            "error_code": detail.get("error_code", "HTTP_ERROR"),
            "message": detail.get("message", str(detail)),
            "details": detail.get("details"),
        }
    return {
        "error_code": "HTTP_ERROR",
        "message": str(detail),
        "details": None,
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global handler for HTTPException."""
    body = _format_http_exception(exc)
    return JSONResponse(status_code=exc.status_code, content=body)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
