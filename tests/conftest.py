from collections.abc import Sequence

import pytest
from django_model_rag import NormalizedDocument
from pytest_django.fixtures import Settings

DocumentStore = dict[str, Sequence[NormalizedDocument]]


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
