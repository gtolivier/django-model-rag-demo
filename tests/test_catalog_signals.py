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


@pytest.mark.django_db
def test_editing_a_category_updates_the_documents_of_its_products(
    rag_store: DocumentStore,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        category = Category.objects.create(name="Kitchen")
        kettle = Product.objects.create(
            name="Kettle",
            description="Boils a litre of water in two minutes.",
            price=Decimal("29.90"),
            category=category,
        )
        toaster = Product.objects.create(
            name="Toaster",
            description="Toasts four slices at once.",
            price=Decimal("39.90"),
            category=category,
        )

    with django_capture_on_commit_callbacks(execute=True):
        category.name = "Cookware"
        category.save()

    [kettle_document] = rag_store[f"catalog.product:{kettle.pk}"]
    [toaster_document] = rag_store[f"catalog.product:{toaster.pk}"]
    assert kettle_document.text.endswith("\n\nCookware")
    assert toaster_document.text.endswith("\n\nCookware")
