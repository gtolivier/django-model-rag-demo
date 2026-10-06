from decimal import Decimal

import pytest
from django.core.management import call_command
from pytest_django.fixtures import Settings

from catalog.models import Category, Product
from tests.conftest import DocumentStore


@pytest.mark.django_db
def test_sync_gives_a_product_one_document_of_its_name_description_and_category(
    rag_store: DocumentStore,
) -> None:
    category = Category.objects.create(name="Kitchen")
    product = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
    )

    call_command("sync_model_rag")

    [document] = rag_store[f"catalog.product:{product.pk}"]
    assert document.title == "Kettle"
    assert document.text == (
        "Kettle\n\nBoils a litre of water in two minutes.\n\nKitchen"
    )
    assert document.url == f"/products/{product.pk}/"


@pytest.mark.django_db
def test_sync_gives_a_product_without_description_a_document_of_its_name_and_category(
    rag_store: DocumentStore,
) -> None:
    category = Category.objects.create(name="Kitchen")
    product = Product.objects.create(
        name="Kettle",
        description="",
        price=Decimal("29.90"),
        category=category,
    )

    call_command("sync_model_rag")

    [document] = rag_store[f"catalog.product:{product.pk}"]
    assert document.text == "Kettle\n\nKitchen"


@pytest.mark.django_db
def test_sync_drops_a_product_deleted_while_the_signals_are_off(
    rag_store: DocumentStore, settings: Settings
) -> None:
    settings.MODEL_RAG_SIGNALS = False
    category = Category.objects.create(name="Kitchen")
    kept = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
    )
    deleted = Product.objects.create(
        name="Toaster",
        description="Browns two slices at once.",
        price=Decimal("39.90"),
        category=category,
    )
    call_command("sync_model_rag")
    deleted_key = f"catalog.product:{deleted.pk}"
    deleted.delete()
    assert deleted_key in rag_store  # no signal fired: the document stayed

    call_command("sync_model_rag")

    assert deleted_key not in rag_store
    assert f"catalog.product:{kept.pk}" in rag_store
