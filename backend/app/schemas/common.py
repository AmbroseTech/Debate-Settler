"""Shared response envelopes and pagination schemas.

Consistent API responses across the app (§67).
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    context: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> Paginated[T]:
        pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(
            items=items, total=total, page=page, page_size=page_size, pages=pages
        )
