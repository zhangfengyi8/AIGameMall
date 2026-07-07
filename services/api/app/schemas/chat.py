from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
