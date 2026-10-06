from decimal import Decimal

import pytest
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_with_signals_off_editing_a_page_or_a_category_syncs_nothing(
    settings: Settings,
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
        page = Page.objects.create(title="FAQ", slug="faq")
        text_block = TextPlugin.objects.create(page=page, body="We make kettles.")
        accordion_item = AccordionItem.objects.create(
            page=page, title="Shipping", body="We ship within two days."
        )
    settings.MODEL_RAG_SIGNALS = False

    with django_capture_on_commit_callbacks(execute=True):
        category.name = "Cookware"
        category.save()
        page.title = "Help"
        page.slug = "help"
        page.save()

    [product_document] = rag_store[f"catalog.product:{product.pk}"]
    [text_document] = rag_store[f"pages.textplugin:{text_block.pk}"]
    [accordion_document] = rag_store[f"pages.accordionitem:{accordion_item.pk}"]
    assert product_document.text.endswith("\n\nKitchen")
    assert text_document.title == "FAQ"
    assert text_document.url == "/pages/faq/"
    assert accordion_document.title == "FAQ — Shipping"
    assert accordion_document.url == "/pages/faq/"
