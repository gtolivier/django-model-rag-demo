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
