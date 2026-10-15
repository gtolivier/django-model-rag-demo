from io import StringIO

import pytest
from django.core.management import call_command
from django_minimal_rag.models import Chunk
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from blog.models import Article


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


@pytest.mark.django_db
def test_embed_pending_embeds_the_waiting_chunks_and_reports_their_count(
    settings: Settings,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    settings.MINIMAL_RAG_EMBEDDINGS = {
        "BACKEND": "django_minimal_rag.embeddings.FakeEmbeddings",
    }
    with django_capture_on_commit_callbacks(execute=True):
        Article.objects.create(
            title="Descaling a kettle",
            body="A cup of vinegar, an hour, and a rinse.",
        )
        Article.objects.create(
            title="Sharpening a knife",
            body="A whetstone, some water, and a steady angle.",
        )
    pending = Chunk.objects.filter(embedding__isnull=True).count()
    assert pending > 0
    stdout = StringIO()

    call_command("embed_pending", stdout=stdout)

    assert f"Embedded {pending} chunks." in stdout.getvalue().splitlines()
    assert not Chunk.objects.filter(embedding__isnull=True).exists()
