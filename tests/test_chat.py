import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.services.ollama_client import OllamaClient
from app.utils.exceptions import OllamaTimeoutError, OllamaUnavailableError


class MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3.5:2b"}]})
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if body["stream"]:
                return httpx.Response(
                    200,
                    content=b'{"message":{"content":"Hello "},"done":false}\n'
                    b'{"message":{"content":"world"},"done":true}\n',
                )
            return httpx.Response(
                200, json={"message": {"content": "A generated answer."}, "done": True}
            )
        return httpx.Response(404)


@pytest.fixture
def client(monkeypatch):
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = MockTransport()
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return TestClient(app)


def test_ollama_status(client):
    response = client.get("/api/v1/ollama/status")
    assert response.status_code == 200
    assert response.json()["model_available"] is True


def test_model_availability_is_false_when_model_is_missing(monkeypatch):
    class MissingModelTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json={"models": [{"name": "other:model"}]})

    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = MissingModelTransport()
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    response = TestClient(app).get("/api/v1/ollama/status")
    assert response.status_code == 200
    assert response.json()["model_available"] is False


def test_successful_chat(client):
    response = client.post("/api/v1/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert response.json()["response"] == "A generated answer."


def test_empty_input_validation(client):
    response = client.post("/api/v1/chat", json={"message": "  "})
    assert response.status_code == 422


def test_streaming_response(client):
    response = client.post("/api/v1/chat/stream", json={"message": "Hello"})
    assert response.status_code == 200
    assert "Hello world" in response.text


@pytest.mark.asyncio
async def test_client_timeout(monkeypatch):
    async def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx.AsyncClient, "get", timeout)
    with pytest.raises(OllamaTimeoutError) as error:
        await OllamaClient(get_settings()).status()
    assert "timed out" in str(error.value).lower()


@pytest.mark.asyncio
async def test_client_connection_failure(monkeypatch):
    async def unavailable(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", unavailable)
    with pytest.raises(OllamaUnavailableError):
        await OllamaClient(get_settings()).status()
