import pytest

from assistant.backends import OllamaEmbeddings


@pytest.mark.parametrize("model", ["nomic-embed-text", "mxbai-embed-large"])
def test_ollama_embeddings_exposes_the_configured_model(model: str) -> None:
    embeddings = OllamaEmbeddings(
        model=model, base_url="http://localhost:11434/v1", timeout=30.0
    )

    assert embeddings.model == model
