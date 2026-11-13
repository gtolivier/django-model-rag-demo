import pytest
from django.apps import apps
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from catalog.models import Category, Product
from tests.rag_output import DocumentStore

ADMIN_MODELS = [
    "blog_article",
    "catalog_category",
    "catalog_product",
    "pages_page",
]

# What a model without __str__ shows in the admin: "Category object (1)".
DEFAULT_OBJECT_LABEL = "object ("


@pytest.fixture
def demo_content(rag_store: DocumentStore) -> None:
    """Load the demo content: the admin shows real rows, not an empty list."""
    call_command("loaddata", "demo", verbosity=0)


@pytest.mark.django_db
@pytest.mark.usefixtures("demo_content")
@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_changelist_names_the_objects(admin_client: Client, model: str) -> None:
    """The list columns and filters show names, not "Category object (1)"."""
    response = admin_client.get(reverse(f"admin:{model}_changelist"))

    assert response.status_code == 200
    assert response.context["cl"].result_count > 0
    assert DEFAULT_OBJECT_LABEL not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("demo_content")
@pytest.mark.parametrize("model", ["blog_article", "catalog_product"])
def test_search_narrows_the_list(admin_client: Client, model: str) -> None:
    response = admin_client.get(reverse(f"admin:{model}_changelist"), {"q": "comté"})

    changelist = response.context["cl"]
    assert 0 < changelist.result_count < changelist.full_result_count


@pytest.mark.django_db
@pytest.mark.usefixtures("demo_content")
def test_products_filter_by_category(admin_client: Client) -> None:
    category = Category.objects.first()
    assert category is not None

    response = admin_client.get(
        reverse("admin:catalog_product_changelist"),
        {"category__id__exact": category.pk},
    )

    expected = Product.objects.filter(category=category).count()
    assert response.context["cl"].result_count == expected


@pytest.mark.django_db
@pytest.mark.usefixtures("demo_content")
@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_change_form_names_the_objects(admin_client: Client, model: str) -> None:
    """The change form, its choices and a page's block inlines show names."""
    obj = apps.get_model(model.replace("_", ".", 1))._default_manager.first()
    assert obj is not None

    response = admin_client.get(reverse(f"admin:{model}_change", args=[obj.pk]))

    assert response.status_code == 200
    assert DEFAULT_OBJECT_LABEL not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("model", ADMIN_MODELS)
def test_add_form_renders(admin_client: Client, model: str) -> None:
    """The add form renders, with the block inlines on a page."""
    response = admin_client.get(reverse(f"admin:{model}_add"))

    assert response.status_code == 200
