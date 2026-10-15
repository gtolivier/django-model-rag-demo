from io import StringIO

import pytest
from django.core.management import call_command
from pytest_django.fixtures import Settings


@pytest.mark.django_db
def test_embed_pending_reports_zero_chunks_when_none_is_waiting(
    settings: Settings,
) -> None:
    settings.MINIMAL_RAG_EMBEDDINGS = {
        "BACKEND": "django_minimal_rag.embeddings.FakeEmbeddings",
    }
    stdout = StringIO()

    call_command("embed_pending", stdout=stdout)

    assert "Embedded 0 chunks." in stdout.getvalue().splitlines()
