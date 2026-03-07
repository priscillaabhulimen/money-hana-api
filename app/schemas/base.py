from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    message: str | None = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str