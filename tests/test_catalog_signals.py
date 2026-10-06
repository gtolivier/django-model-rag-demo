from decimal import Decimal

import pytest
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks

from catalog.models import Category, Product
from tests.conftest import DocumentStore


@pytest.mark.django_db
def test_saving_a_product_updates_its_document_when_the_transaction_commits(
    rag_store: DocumentStore,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        category = Category.objects.create(name="Kitchen")
        product = Product.objects.create(
            name="Kettle",
            description="Boils a litre of water in two minutes.",
            price=Decimal("29.90"),
            category=category,
        )
    key = f"catalog.product:{product.pk}"

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        product.description = "Boils a litre of water in ninety seconds."
        product.save()

    [document_before_commit] = rag_store[key]
    assert document_before_commit.text == (
        "Kettle\n\nBoils a litre of water in two minutes.\n\nKitchen"
    )

    for callback in callbacks:
        callback()

    [document_after_commit] = rag_store[key]
    assert document_after_commit.text == (
        "Kettle\n\nBoils a litre of water in ninety seconds.\n\nKitchen"
    )
