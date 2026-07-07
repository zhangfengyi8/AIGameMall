"""统一响应格式。"""

from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ApiResponse(BaseModel):
    """统一 API 响应结构。"""
    success: bool = True
    code: str = "OK"
    message: str = "success"
    data: Any | None = None
    request_id: str | None = None


def ok(data: Any = None, request_id: str | None = None) -> dict:
    return {
        "success": True,
        "code": "OK",
        "message": "success",
        "data": data,
        "request_id": request_id,
    }


def error(code: str, message: str, data: Any = None, request_id: str | None = None) -> dict:
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }