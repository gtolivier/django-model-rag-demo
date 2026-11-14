import pytest
from django.core.management import call_command
from django.db.models import Model
from django_model_rag.documents import model_source_key

from blog.models import Article
from catalog.models import Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore

SOURCES: tuple[type[Model], ...] = (Article, Product, AccordionItem, TextPlugin)


@pytest.mark.django_db
def test_the_demo_fixture_gives_each_source_documents_once_synced(
    rag_store: DocumentStore,
) -> None:
    call_command("loaddata", "demo", verbosity=0)
    call_command("sync_model_rag")

    for model in SOURCES:
        label = model._meta.label_lower
        pks = list(model._default_manager.values_list("pk", flat=True))
        assert pks, f"the fixture has no {label}"
        for pk in pks:
            documents = rag_store.get(model_source_key(model, pk), ())
            assert documents, f"{label}:{pk} has no document"
            assert all(document.text.strip() for document in documents), pk


@pytest.mark.django_db
def test_the_demo_fixture_mirrors_its_english_content_in_french() -> None:
    call_command("loaddata", "demo", verbosity=0)

    counts = {
        label: {
            language: queryset.filter(**{lookup: language}).count()
            for language in ("en", "fr")
        }
        for label, queryset, lookup in (
            ("articles", Article.objects.all(), "language"),
            ("products", Product.objects.all(), "language"),
            ("pages", Page.objects.all(), "language"),
            ("text blocks", TextPlugin.objects.all(), "page__language"),
            ("accordion items", AccordionItem.objects.all(), "page__language"),
        )
    }
    for label, by_language in counts.items():
        assert by_language["fr"], f"the fixture has no French {label}"
        assert by_language["fr"] == by_language["en"], (label, by_language)

    french_categories = set(
        Product.objects.filter(language="fr").values_list("category", flat=True)
    )
    english_categories = set(
        Product.objects.filter(language="en").values_list("category", flat=True)
    )
    assert not french_categories & english_categories
