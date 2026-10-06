from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Category, Product
from pages.models import Page
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_product_and_page_views_respond_in_plain_text(
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
    assert product_response["Content-Type"].startswith("text/plain")
    assert page_response["Content-Type"].startswith("text/plain")
