from decimal import Decimal

import pytest
from django.core.management import call_command

from catalog.models import Category, Product
from tests.rag_output import DocumentStore


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
def test_sync_gives_a_product_document_the_product_language(
    rag_store: DocumentStore,
) -> None:
    category = Category.objects.create(name="Kitchen")
    english = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
        language="en",
    )
    french = Product.objects.create(
        name="Bouilloire",
        description="Fait bouillir un litre d'eau en deux minutes.",
        price=Decimal("29.90"),
        category=category,
        language="fr",
    )

    call_command("sync_model_rag")

    [english_document] = rag_store[f"catalog.product:{english.pk}"]
    [french_document] = rag_store[f"catalog.product:{french.pk}"]
    assert english_document.language == "en"
    assert french_document.language == "fr"
