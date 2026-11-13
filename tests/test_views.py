from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_product_and_page_views_respond_in_escaped_html(
    client: Client, rag_store: DocumentStore
) -> None:
    category = Category.objects.create(name="Kitchen")
    product = Product.objects.create(
        name="<b>Kettle</b>",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
    )
    Page.objects.create(title="<i>FAQ</i>", slug="faq")

    product_response = client.get(reverse("product_detail", args=[product.pk]))
    page_response = client.get(reverse("page_detail", args=["faq"]))

    assert product_response.status_code == 200
    assert page_response.status_code == 200
    assert product_response["Content-Type"].startswith("text/html")
    assert page_response["Content-Type"].startswith("text/html")
    product_content = product_response.content.decode()
    page_content = page_response.content.decode()
    assert escape("<b>Kettle</b>") in product_content
    assert "<b>Kettle</b>" not in product_content
    assert escape("<i>FAQ</i>") in page_content
    assert "<i>FAQ</i>" not in page_content


@pytest.mark.django_db
def test_product_view_shows_its_price_and_category_name(
    client: Client, rag_store: DocumentStore
) -> None:
    category = Category.objects.create(name="Small appliances")
    product = Product.objects.create(
        name="Toaster",
        description="Browns two slices at once.",
        price=Decimal("29.90"),
        category=category,
    )

    response = client.get(product.get_absolute_url())

    assert response.status_code == 200
    content = response.content.decode()
    assert "29.90" in content
    assert "Small appliances" in content


@pytest.mark.django_db
def test_page_view_shows_the_text_of_its_blocks(
    client: Client, rag_store: DocumentStore
) -> None:
    page = Page.objects.create(title="About us", slug="about")
    TextPlugin.objects.create(page=page, body="We make kettles.")
    TextPlugin.objects.create(page=page, body="Since 1998.")
    AccordionItem.objects.create(
        page=page, title="Shipping", body="We ship within two days."
    )

    response = client.get(page.get_absolute_url())

    assert response.status_code == 200
    content = response.content.decode()
    assert "About us" in content
    assert "We make kettles." in content
    assert "Since 1998." in content
    assert "Shipping" in content
    assert "We ship within two days." in content
