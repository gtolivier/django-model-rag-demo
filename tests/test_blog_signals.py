import pytest
from django_minimal_rag.models import Chunk
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from blog.models import Article


@pytest.mark.django_db
def test_saving_an_article_stores_its_text_in_chunks_left_for_embed_pending(
    settings: Settings,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    settings.MINIMAL_RAG_EMBEDDINGS = {
        "BACKEND": "django_minimal_rag.embeddings.FakeEmbeddings",
    }

    with django_capture_on_commit_callbacks(execute=True):
        article = Article.objects.create(
            title="Descaling a kettle",
            body="A cup of vinegar, an hour, and a rinse.",
        )

    chunks = list(Chunk.objects.all())
    assert any(article.body in chunk.text for chunk in chunks)
    assert all(chunk.embedding is None for chunk in chunks)
