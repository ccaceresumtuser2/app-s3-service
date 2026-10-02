from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiError(BaseModel):
    code: str
    message: str
    field: str | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool
    message: str
    data: DataT | None = None
    errors: list[ApiError] = Field(default_factory=list)