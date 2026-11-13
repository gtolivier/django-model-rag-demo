import pytest
from django.test import Client
from django.urls import reverse

ADMIN_MODELS = [
    "blog_article",
    "catalog_category",
    "catalog_product",
    "pages_page",
]


@pytest.mark.django_db
@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_changelist_searches_and_filters(admin_client: Client, model: str) -> None:
    """The list columns, search fields and filters name real fields."""
    response = admin_client.get(reverse(f"admin:{model}_changelist"), {"q": "comté"})

    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_add_form_renders(admin_client: Client, model: str) -> None:
    """The add form renders, with the block inlines on a page."""
    response = admin_client.get(reverse(f"admin:{model}_add"))

    assert response.status_code == 200
