from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import Field

from app.core.schema import AppBaseModel

T = TypeVar("T")


class PaginationMeta(AppBaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class StandardResponse(AppBaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation successful"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: T | None = None
    errors: list[str] | None = None


class PaginatedResponse(AppBaseModel, Generic[T]):
    success: bool = True
    message: str = "Records fetched successfully"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: list[T]
    pagination: PaginationMeta
    errors: list[str] | None = None
