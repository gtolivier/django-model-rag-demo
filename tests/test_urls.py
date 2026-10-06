from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import resolve

from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore


def _captured_values(url: str) -> list[str]:
    """Resolve ``url`` and give what its route captured, as strings."""
    match = resolve(url)
    return [str(value) for value in (*match.args, *match.kwargs.values())]


@pytest.mark.django_db
def test_each_document_url_resolves_to_a_route_capturing_its_object(
    rag_store: DocumentStore,
) -> None:
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

    call_command("sync_model_rag")

    [product_document] = rag_store[f"catalog.product:{product.pk}"]
    [text_document] = rag_store[f"pages.textplugin:{text_block.pk}"]
    [accordion_document] = rag_store[f"pages.accordionitem:{accordion_item.pk}"]
    assert str(product.pk) in _captured_values(product_document.url)
    assert "faq" in _captured_values(text_document.url)
    assert "faq" in _captured_values(accordion_document.url)
