"""Common Pydantic schemas: StatusOr, APIError, HealthResponse."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class StatusOr(BaseModel, Generic[T]):
    """Generic result wrapper for service-layer operations."""

    success: bool
    data: T | None = None
    error_bucket: str | None = None
    message: str | None = None

    @classmethod
    def ok(cls, data: T) -> "StatusOr[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error_bucket: str, message: str) -> "StatusOr[None]":
        return cls(success=False, error_bucket=error_bucket, message=message)

    @classmethod
    def error(cls, error_bucket: str, message: str) -> "StatusOr[None]":
        return cls(success=False, error_bucket=error_bucket, message=message)


class APIError(BaseModel):
    """API error response schema."""

    error_code: str
    message: str
    details: dict | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    environment: str
    postgres: str
    redis: str
