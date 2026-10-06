import pytest
from django.core.management import call_command

from blog.models import Article
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_sync_gives_an_article_one_document_titled_by_its_title_of_its_title_and_body(
    rag_store: DocumentStore,
) -> None:
    article = Article.objects.create(
        title="Descaling a kettle",
        body="A cup of vinegar, an hour, and a rinse.",
    )

    call_command("sync_model_rag")

    [document] = rag_store[f"blog.article:{article.pk}"]
    assert document.title == "Descaling a kettle"
    assert document.text == (
        "Descaling a kettle\n\nA cup of vinegar, an hour, and a rinse."
    )
