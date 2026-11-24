from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=512, ge=1, le=100_000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    response: str
    model: str
    done: bool = True
    session_id: str | None = None
    sources: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)


class ResetResponse(BaseModel):
    message: str
    session_id: str
