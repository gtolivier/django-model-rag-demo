import importlib
import json
from collections.abc import Iterator

import httpx
import pytest
from django_minimal_rag.embeddings import get_embeddings
from django_minimal_rag.llm import get_llm
from pytest_django.fixtures import Settings

import config.settings
from assistant.backends import OllamaEmbeddings, OllamaLLM


@pytest.fixture
def settings_env() -> Iterator[pytest.MonkeyPatch]:
    """Give the test a monkeypatch for the environment `config.settings` reads.

    Once the variables are restored, the module is reloaded again so that no
    other test sees the values computed from them.
    """
    with pytest.MonkeyPatch.context() as env:
        yield env
    importlib.reload(config.settings)


def test_project_settings_build_the_default_ollama_backends() -> None:
    embeddings = get_embeddings()
    llm = get_llm()

    assert isinstance(embeddings, OllamaEmbeddings)
    assert embeddings.model == "bge-m3"
    assert embeddings.base_url == "http://localhost:11434/v1"
    assert isinstance(llm, OllamaLLM)
    assert llm.model == "mistral-small3.2"
    assert llm.base_url == "http://localhost:11434/v1"


def test_rag_environment_variables_override_the_ollama_backend_defaults(
    settings_env: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings_env.setenv("RAG_BASE_URL", "http://ollama.internal:8080/v1")
    settings_env.setenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
    settings_env.setenv("RAG_LLM_MODEL", "llama3.2")
    reloaded = importlib.reload(config.settings)
    settings.MINIMAL_RAG_EMBEDDINGS = reloaded.MINIMAL_RAG_EMBEDDINGS
    settings.MINIMAL_RAG_LLM = reloaded.MINIMAL_RAG_LLM

    embeddings = get_embeddings()
    llm = get_llm()

    assert isinstance(embeddings, OllamaEmbeddings)
    assert embeddings.model == "nomic-embed-text"
    assert embeddings.base_url == "http://ollama.internal:8080/v1"
    assert isinstance(llm, OllamaLLM)
    assert llm.model == "llama3.2"
    assert llm.base_url == "http://ollama.internal:8080/v1"


@pytest.mark.parametrize("model", ["nomic-embed-text", "mxbai-embed-large"])
def test_ollama_embeddings_exposes_the_configured_model(model: str) -> None:
    embeddings = OllamaEmbeddings(
        model=model, base_url="http://localhost:11434/v1", timeout=30.0
    )

    assert embeddings.model == model


def test_ollama_embeddings_embed_posts_to_the_openai_compatible_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                "model": "nomic-embed-text",
            },
        )

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
        timeout=30.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    vectors = embeddings.embed(["a text"])

    assert vectors == [[0.1, 0.2]]
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "http://localhost:11434/v1/embeddings"
    assert json.loads(requests[0].content) == {
        "model": "nomic-embed-text",
        "input": ["a text"],
    }


def test_ollama_embeddings_embed_orders_vectors_by_the_index_of_their_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"object": "embedding", "index": 2, "embedding": [0.3, 0.3]},
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.1]},
                    {"object": "embedding", "index": 1, "embedding": [0.2, 0.2]},
                ],
                "model": "nomic-embed-text",
            },
        )

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
        timeout=30.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    vectors = embeddings.embed(["first", "second", "third"])

    assert vectors == [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]


def test_ollama_embeddings_embed_sends_requests_with_the_configured_timeout() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                "model": "nomic-embed-text",
            },
        )

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
        timeout=120.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    embeddings.embed(["a text"])

    assert len(requests) == 1
    assert requests[0].extensions["timeout"] == {
        "connect": 120.0,
        "read": 120.0,
        "write": 120.0,
        "pool": 120.0,
    }


def test_ollama_embeddings_embed_raises_when_the_server_answers_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model runner crashed"})

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
        timeout=30.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(httpx.HTTPStatusError):
        embeddings.embed(["a text"])


@pytest.mark.parametrize(
    ("model", "prompt", "system", "answer"),
    [
        (
            "llama3.2",
            "Which books mention Lyon?",
            "Answer from the context only.",
            "Two books mention Lyon.",
        ),
        (
            "mistral",
            "Quel est le prix du vélo ?",
            "Réponds en français, brièvement.",
            "Le vélo coûte 450 euros.",
        ),
    ],
)
def test_ollama_llm_complete_posts_the_chat_and_returns_the_answer(
    model: str, prompt: str, system: str, answer: str
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "chat.completion",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": answer},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    llm = OllamaLLM(
        model=model,
        base_url="http://localhost:11434/v1",
        timeout=30.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    completion = llm.complete(prompt, system=system)

    assert completion == answer
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "http://localhost:11434/v1/chat/completions"
    assert json.loads(requests[0].content) == {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }


def test_ollama_llm_complete_sends_requests_with_the_configured_timeout() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "chat.completion",
                "model": "llama3.2",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "An answer."},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    llm = OllamaLLM(
        model="llama3.2",
        base_url="http://localhost:11434/v1",
        timeout=90.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    llm.complete("Which books mention Lyon?", system="Answer briefly.")

    assert len(requests) == 1
    assert requests[0].extensions["timeout"] == {
        "connect": 90.0,
        "read": 90.0,
        "write": 90.0,
        "pool": 90.0,
    }


def test_ollama_llm_complete_raises_when_the_server_answers_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model runner crashed"})

    llm = OllamaLLM(
        model="llama3.2",
        base_url="http://localhost:11434/v1",
        timeout=30.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(httpx.HTTPStatusError):
        llm.complete("Which books mention Lyon?", system="Answer briefly.")
