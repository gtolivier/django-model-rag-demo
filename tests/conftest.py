import pytest
from pytest_django.fixtures import Settings

from tests.rag_output import DocumentStore


@pytest.fixture
def rag_store(settings: Settings) -> DocumentStore:
    """Point the output at a fresh dict and give it to the test.

    The setting is in place before the test creates any object: the package
    checks it before every save of a registered model.
    """
    store: DocumentStore = {}
    settings.MODEL_RAG_OUTPUT = {
        "BACKEND": "tests.rag_output.DictOutput",
        "OPTIONS": {"store": store},
    }
    return store


@pytest.fixture
def fake_embeddings(settings: Settings) -> None:
    """Embed with django-minimal-rag's fake backend instead of Ollama."""
    settings.MINIMAL_RAG_EMBEDDINGS = {
        "BACKEND": "django_minimal_rag.embeddings.FakeEmbeddings",
    }
