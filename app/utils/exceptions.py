class OllamaError(Exception):
    """Base error for Ollama integration failures."""


class OllamaUnavailableError(OllamaError):
    """Raised when Ollama cannot be reached."""


class OllamaModelError(OllamaError):
    """Raised when Ollama rejects a model request."""


class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request times out."""
