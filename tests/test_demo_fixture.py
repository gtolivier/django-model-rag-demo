import pytest
from django.core.management import call_command
from django.db.models import Model

from blog.models import Article
from catalog.models import Product
from pages.models import AccordionItem, TextPlugin
from tests.rag_output import DocumentStore

SOURCES: dict[str, type[Model]] = {
    "blog.article": Article,
    "catalog.product": Product,
    "pages.accordionitem": AccordionItem,
    "pages.textplugin": TextPlugin,
}


@pytest.mark.django_db
def test_the_demo_fixture_gives_each_source_documents_once_synced(
    rag_store: DocumentStore,
) -> None:
    call_command("loaddata", "demo", verbosity=0)
    call_command("sync_model_rag")

    expected_keys = {
        f"{label}:{pk}"
        for label, model in SOURCES.items()
        for pk in model._default_manager.values_list("pk", flat=True)
    }
    for label in SOURCES:
        assert any(key.startswith(f"{label}:") for key in expected_keys), label
    assert set(rag_store) == expected_keys
