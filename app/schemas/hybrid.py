from typing import Any

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedPage(BaseModel):
    url: str
    title: str = ""
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)


class ToolInfo(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    server: str = ""
    tool_type: str = "mcp"
    available: bool = True


class ToolExecutionResult(BaseModel):
    tool: str
    server: str
    success: bool
    output: Any = None
    error: str | None = None
