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


@pytest.mark.django_db
def test_sync_gives_an_article_document_the_article_language(
    rag_store: DocumentStore,
) -> None:
    english = Article.objects.create(
        title="Descaling a kettle",
        body="A cup of vinegar, an hour, and a rinse.",
        language="en",
    )
    french = Article.objects.create(
        title="Détartrer une bouilloire",
        body="Une tasse de vinaigre, une heure, et un rinçage.",
        language="fr",
    )

    call_command("sync_model_rag")

    [english_document] = rag_store[f"blog.article:{english.pk}"]
    [french_document] = rag_store[f"blog.article:{french.pk}"]
    assert english_document.language == "en"
    assert french_document.language == "fr"
