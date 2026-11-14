from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import Resolver404, resolve, reverse
from django.utils import translation

from blog.models import Article
from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore


def _captured_values(url: str) -> list[str]:
    """Resolve ``url`` and give what its route captured, as strings.

    A url no route matches (an empty one included) fails the test,
    naming that url.
    """
    try:
        match = resolve(url)
    except Resolver404:
        pytest.fail(f"{url!r} resolves to no route")
    return [str(value) for value in (*match.args, *match.kwargs.values())]


def _absolute_url_with_active_language(
    language: str, instance: Article | Product | Page
) -> str:
    with translation.override(language):
        return instance.get_absolute_url()


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


@pytest.mark.django_db
def test_an_article_document_url_resolves_to_a_route_capturing_the_article(
    rag_store: DocumentStore,
) -> None:
    article = Article.objects.create(
        title="Descaling a kettle",
        body="A cup of vinegar, an hour, and a rinse.",
    )

    call_command("sync_model_rag")

    [article_document] = rag_store[f"blog.article:{article.pk}"]
    assert str(article.pk) in _captured_values(article_document.url)


@pytest.mark.django_db
def test_a_product_url_is_in_the_product_language_whatever_the_active_one() -> None:
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
        price=Decimal("31.40"),
        category=category,
        language="fr",
    )

    french_url = _absolute_url_with_active_language("en", french)
    english_url = _absolute_url_with_active_language("fr", english)

    assert french_url == f"/fr/products/{french.pk}/"
    assert english_url == f"/products/{english.pk}/"


@pytest.mark.django_db
def test_an_article_url_is_in_the_article_language_whatever_the_active_one() -> None:
    english = Article.objects.create(
        title="Descaling a kettle",
        body="A cup of vinegar, an hour, and a rinse.",
        language="en",
    )
    french = Article.objects.create(
        title="Détartrer une bouilloire",
        body="Une tasse de vinaigre, une heure, et un rinçage.",
        language="fr",
    )

    french_url = _absolute_url_with_active_language("en", french)
    english_url = _absolute_url_with_active_language("fr", english)

    assert french_url == f"/fr/blog/{french.pk}/"
    assert english_url == f"/blog/{english.pk}/"


@pytest.mark.django_db
def test_a_page_url_is_in_the_page_language_whatever_the_active_one() -> None:
    english = Page.objects.create(title="FAQ", slug="faq", language="en")
    french = Page.objects.create(title="Questions", slug="questions", language="fr")

    french_url = _absolute_url_with_active_language("en", french)
    english_url = _absolute_url_with_active_language("fr", english)

    assert french_url == f"/fr/pages/{french.slug}/"
    assert english_url == f"/pages/{english.slug}/"


def test_the_admin_index_stays_outside_the_language_prefix_in_french() -> None:
    with translation.override("fr"):
        assert reverse("admin:index") == "/admin/"
