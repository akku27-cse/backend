from functools import lru_cache
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT", "300"))
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    search_provider: str = os.getenv("SEARCH_PROVIDER", "tavily").lower()
    search_api_key: str = os.getenv("SEARCH_API_KEY", "")
    search_endpoint: str = os.getenv(
        "SEARCH_ENDPOINT", "https://api.tavily.com/search"
    )
    search_timeout: float = float(os.getenv("SEARCH_TIMEOUT", "20"))
    search_result_count: int = int(os.getenv("SEARCH_RESULT_COUNT", "5"))
    extraction_timeout: float = float(os.getenv("EXTRACTION_TIMEOUT", "20"))
    extraction_max_chars: int = int(os.getenv("EXTRACTION_MAX_CHARS", "12000"))
    mcp_servers_json: str = os.getenv("MCP_SERVERS_JSON", "[]")
    mcp_timeout: float = float(os.getenv("MCP_TIMEOUT", "30"))
    max_tool_rounds: int = int(os.getenv("MAX_TOOL_ROUNDS", "3"))
    mcp_auto_connect: bool = os.getenv("MCP_AUTO_CONNECT", "true").lower() == "true"
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    chroma_persist_directory: str = os.getenv(
        "CHROMA_PERSIST_DIRECTORY", "./data/chroma"
    )
    document_storage_directory: str = os.getenv(
        "DOCUMENT_STORAGE_DIRECTORY", "./data/documents"
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    rag_similarity_threshold: float = float(
        os.getenv("RAG_SIMILARITY_THRESHOLD", "0.0")
    )
    agent_max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "8"))
    agent_timeout: float = float(os.getenv("AGENT_TIMEOUT", "300"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
