import json

import httpx
import pytest

from assistant.backends import OllamaEmbeddings


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
