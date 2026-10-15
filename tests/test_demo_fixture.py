import pytest
from django.core.management import call_command
from django.db.models import Model
from django_model_rag.documents import model_source_key

from blog.models import Article
from catalog.models import Product
from pages.models import AccordionItem, TextPlugin
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
