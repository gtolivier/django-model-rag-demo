from collections.abc import Iterator

import pytest
from django.utils import translation
from pytest_django.fixtures import Settings

from tests.rag_output import DocumentStore


@pytest.fixture(autouse=True)
def _reset_active_language() -> Iterator[None]:
    """Give every test the default language back.

    LocaleMiddleware activates the request's language in the test thread and
    nothing deactivates it: after a request under /fr/, the next test's
    `reverse()` would build French URLs.
    """
    yield
    translation.deactivate()


@pytest.fixture(scope="session")
def _allow_the_orm_beside_playwright() -> Iterator[None]:
    """Let Django's ORM run while Playwright's event loop is running.

    Playwright's sync API keeps an event loop running in the test thread for
    the whole session, and Django refuses ORM calls from such a thread: the
    database setup and teardown of a live_server test would fail. Session
    scoped, so it still holds when the test database is flushed.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
        yield


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
