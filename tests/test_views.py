from collections.abc import Sequence
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from blog.models import Article
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
def test_product_list_shows_every_product_name_with_a_link_to_its_page(
    client: Client, rag_store: DocumentStore
) -> None:
    category = Category.objects.create(name="Kitchen")
    kettle = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
    )
    toaster = Product.objects.create(
        name="Toaster",
        description="Browns two slices at once.",
        price=Decimal("24.50"),
        category=category,
    )

    url = reverse("product_list")
    response = client.get(url)

    assert url == "/products/"
    assert response.status_code == 200
    content = response.content.decode()
    for product in (kettle, toaster):
        assert product.name in content
        assert f'href="{product.get_absolute_url()}"' in content


@pytest.mark.django_db
def test_article_list_shows_every_article_title_with_a_link_to_its_page(
    client: Client, rag_store: DocumentStore
) -> None:
    descaling = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
    )
    toasting = Article.objects.create(
        title="Toasting bagels",
        body="Use the bagel setting to brown only the cut side.",
    )

    url = reverse("article_list")
    response = client.get(url)

    assert url == "/blog/"
    assert response.status_code == 200
    content = response.content.decode()
    for article in (descaling, toasting):
        assert article.title in content
        assert f'href="{article.get_absolute_url()}"' in content


def _assert_in_order(content: str, needles: Sequence[str]) -> None:
    positions = [content.index(needle) for needle in needles]
    assert positions == sorted(positions)


def _create_three_articles_oldest_first() -> tuple[Article, Article, Article]:
    oldest = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
    )
    middle = Article.objects.create(
        title="Toasting bagels",
        body="Use the bagel setting to brown only the cut side.",
    )
    newest = Article.objects.create(
        title="Sharpening knives",
        body="Hold the blade at twenty degrees against the stone.",
    )
    return oldest, middle, newest


@pytest.mark.django_db
def test_article_list_shows_the_most_recently_created_article_first(
    client: Client, rag_store: DocumentStore
) -> None:
    oldest, middle, newest = _create_three_articles_oldest_first()

    response = client.get(reverse("article_list"))

    assert response.status_code == 200
    _assert_in_order(
        response.content.decode(),
        [
            f'href="{article.get_absolute_url()}"'
            for article in (newest, middle, oldest)
        ],
    )


@pytest.mark.django_db
def test_article_list_keeps_an_edited_older_article_after_the_newer_ones(
    client: Client, rag_store: DocumentStore
) -> None:
    oldest, middle, newest = _create_three_articles_oldest_first()
    oldest.body = "Fill it with citric acid and leave it for an hour."
    oldest.save()

    response = client.get(reverse("article_list"))

    assert response.status_code == 200
    _assert_in_order(
        response.content.decode(),
        [
            f'href="{article.get_absolute_url()}"'
            for article in (newest, middle, oldest)
        ],
    )


@pytest.mark.django_db
def test_article_list_shows_only_the_articles_of_the_active_language(
    client: Client, rag_store: DocumentStore
) -> None:
    english = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
        language="en",
    )
    french = Article.objects.create(
        title="Détartrer une bouilloire",
        body="Remplissez-la de vinaigre blanc et laissez agir une nuit.",
        language="fr",
    )

    english_response = client.get("/blog/")
    french_response = client.get("/fr/blog/")

    assert english_response.status_code == 200
    english_content = english_response.content.decode()
    assert english.title in english_content
    assert french.title not in english_content
    assert french_response.status_code == 200
    french_content = french_response.content.decode()
    assert french.title in french_content
    assert english.title not in french_content


@pytest.mark.django_db
def test_article_view_does_not_find_an_article_of_the_other_language(
    client: Client, rag_store: DocumentStore
) -> None:
    english = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
        language="en",
    )
    french = Article.objects.create(
        title="Détartrer une bouilloire",
        body="Remplissez-la de vinaigre blanc et laissez agir une nuit.",
        language="fr",
    )

    french_under_root = client.get(f"/blog/{french.pk}/")
    english_under_fr = client.get(f"/fr/blog/{english.pk}/")

    assert french_under_root.status_code == 404
    assert english_under_fr.status_code == 404


@pytest.mark.django_db
def test_nav_lists_pages_in_creation_order_even_after_the_oldest_is_edited(
    client: Client, rag_store: DocumentStore
) -> None:
    oldest = Page.objects.create(title="About us", slug="about")
    middle = Page.objects.create(title="FAQ", slug="faq")
    newest = Page.objects.create(title="Delivery", slug="delivery")
    oldest.title = "Our story"
    oldest.save()

    response = client.get(reverse("product_list"))

    assert response.status_code == 200
    _assert_in_order(
        response.content.decode(),
        [f'href="{page.get_absolute_url()}"' for page in (oldest, middle, newest)],
    )


@pytest.mark.django_db
def test_home_page_links_to_the_product_list_the_article_list_and_every_page(
    client: Client, rag_store: DocumentStore
) -> None:
    about = Page.objects.create(title="About us", slug="about")
    faq = Page.objects.create(title="FAQ", slug="faq")

    url = reverse("home")
    response = client.get(url)

    assert url == "/"
    assert response.status_code == 200
    content = response.content.decode()
    assert f'href="{reverse("product_list")}"' in content
    assert f'href="{reverse("article_list")}"' in content
    for page in (about, faq):
        assert f'href="{page.get_absolute_url()}"' in content


@pytest.mark.django_db
def test_home_page_is_served_in_english_at_the_root_and_in_french_under_fr(
    client: Client, rag_store: DocumentStore
) -> None:
    english_response = client.get("/")
    french_response = client.get("/fr/")

    assert english_response.status_code == 200
    assert english_response.headers.get("Content-Language") == "en"
    assert french_response.status_code == 200
    assert french_response.headers.get("Content-Language") == "fr"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    ["product_list", "product_detail", "page_detail", "article_list", "article_detail"],
)
def test_every_view_links_to_the_product_list_the_article_list_and_every_page(
    client: Client, rag_store: DocumentStore, view: str
) -> None:
    product = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=Category.objects.create(name="Kitchen"),
    )
    article = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
    )
    about = Page.objects.create(title="About us", slug="about")
    faq = Page.objects.create(title="FAQ", slug="faq")
    urls = {
        "product_list": reverse("product_list"),
        "product_detail": product.get_absolute_url(),
        "page_detail": about.get_absolute_url(),
        "article_list": reverse("article_list"),
        "article_detail": article.get_absolute_url(),
    }

    response = client.get(urls[view])

    assert response.status_code == 200
    content = response.content.decode()
    assert f'href="{reverse("product_list")}"' in content
    assert f'href="{reverse("article_list")}"' in content
    for page in (about, faq):
        assert f'href="{page.get_absolute_url()}"' in content


@pytest.mark.django_db
def test_product_list_shows_each_product_category_name_and_price(
    client: Client, rag_store: DocumentStore
) -> None:
    Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=Category.objects.create(name="Small appliances"),
    )
    Product.objects.create(
        name="Rake",
        description="Gathers leaves without scratching the lawn.",
        price=Decimal("14.75"),
        category=Category.objects.create(name="Garden tools"),
    )

    response = client.get(reverse("product_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Small appliances" in content
    assert "29.90" in content
    assert "Garden tools" in content
    assert "14.75" in content


@pytest.mark.django_db
def test_product_list_shows_only_the_products_of_the_active_language(
    client: Client, rag_store: DocumentStore
) -> None:
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

    english_response = client.get("/products/")
    french_response = client.get("/fr/products/")

    assert english_response.status_code == 200
    english_content = english_response.content.decode()
    assert english.name in english_content
    assert french.name not in english_content
    assert french_response.status_code == 200
    french_content = french_response.content.decode()
    assert french.name in french_content
    assert english.name not in french_content


@pytest.mark.django_db
def test_product_view_does_not_find_a_product_of_the_other_language(
    client: Client, rag_store: DocumentStore
) -> None:
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

    french_under_root = client.get(f"/products/{french.pk}/")
    english_under_fr = client.get(f"/fr/products/{english.pk}/")

    assert french_under_root.status_code == 404
    assert english_under_fr.status_code == 404


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


@pytest.mark.django_db
def test_page_view_shows_its_text_blocks_in_pk_order_whatever_the_insertion_order(
    client: Client, rag_store: DocumentStore
) -> None:
    page = Page.objects.create(title="About us", slug="about")
    later = TextPlugin.objects.create(pk=10, page=page, body="Since 1998.")
    earlier = TextPlugin.objects.create(pk=5, page=page, body="We make kettles.")

    response = client.get(page.get_absolute_url())

    assert response.status_code == 200
    _assert_in_order(
        response.content.decode(), [block.body for block in (earlier, later)]
    )


@pytest.mark.django_db
def test_page_view_shows_its_accordion_items_in_pk_order_whatever_the_insertion_order(
    client: Client, rag_store: DocumentStore
) -> None:
    page = Page.objects.create(title="FAQ", slug="faq")
    later = AccordionItem.objects.create(
        pk=10, page=page, title="Returns", body="Returns are free for 30 days."
    )
    earlier = AccordionItem.objects.create(
        pk=5, page=page, title="Shipping", body="We ship within two days."
    )

    response = client.get(page.get_absolute_url())

    assert response.status_code == 200
    _assert_in_order(
        response.content.decode(), [item.body for item in (earlier, later)]
    )


@pytest.mark.django_db
def test_article_view_shows_its_title_and_body(
    client: Client, rag_store: DocumentStore
) -> None:
    article = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
    )

    response = client.get(article.get_absolute_url())

    assert response.status_code == 200
    content = response.content.decode()
    assert "Descaling a kettle" in content
    assert "Fill it with white vinegar and leave it overnight." in content
