import pytest
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks

from blog.models import Article
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_saving_an_article_updates_its_document_when_the_transaction_commits(
    rag_store: DocumentStore,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        article = Article.objects.create(
            title="Descaling a kettle",
            body="A cup of vinegar, an hour, and a rinse.",
        )
    key = f"blog.article:{article.pk}"

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        article.body = "A cup of citric acid, half an hour, and a rinse."
        article.save()

    [document_before_commit] = rag_store[key]
    assert document_before_commit.text == (
        "Descaling a kettle\n\nA cup of vinegar, an hour, and a rinse."
    )

    for callback in callbacks:
        callback()

    [document_after_commit] = rag_store[key]
    assert document_after_commit.text == (
        "Descaling a kettle\n\nA cup of citric acid, half an hour, and a rinse."
    )
