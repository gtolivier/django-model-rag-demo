import re
from collections.abc import Sequence
from decimal import Decimal
from html.parser import HTMLParser
from io import StringIO
from urllib.parse import urlsplit

import httpx
import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext, override
from django_minimal_rag.answering import Answer, Exchange
from django_minimal_rag.retrieval import RetrievedChunk

from assistant.answering import MAX_CHUNKS, MAX_DISTANCE, NOTHING_CLOSE_ENOUGH
from blog.models import Article
from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from pages.views import QUESTION_REQUIRED
from tests.chat_answers import (
    CHAT_ANSWER,
    answer_each_question_from,
    answer_every_question_with,
)
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


def _create_an_english_and_a_french_article() -> tuple[Article, Article]:
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
    return english, french


@pytest.mark.django_db
def test_article_list_shows_only_the_articles_of_the_active_language(
    client: Client, rag_store: DocumentStore
) -> None:
    english, french = _create_an_english_and_a_french_article()

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
    english, french = _create_an_english_and_a_french_article()

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
def test_nav_lists_only_the_pages_of_the_active_language(
    client: Client, rag_store: DocumentStore
) -> None:
    english = Page.objects.create(title="Delivery", slug="delivery", language="en")
    french = Page.objects.create(title="Livraison", slug="livraison", language="fr")

    english_response = client.get("/")
    french_response = client.get("/fr/")

    assert english_response.status_code == 200
    assert list(english_response.context["nav_pages"]) == [english]
    assert french_response.status_code == 200
    assert list(french_response.context["nav_pages"]) == [french]


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


class _PostForms(HTMLParser):
    """Collect each POST form of a page as (action, field names), in order."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[tuple[str, set[str]]] = []
        self._names: set[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            if (attributes.get("method") or "").lower() == "post":
                self._names = set()
                self.forms.append((attributes.get("action") or "", self._names))
            else:
                self._names = None
        elif self._names is not None and attributes.get("name"):
            self._names.add(attributes["name"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._names = None


def _post_forms(content: str) -> list[tuple[str, set[str]]]:
    parser = _PostForms()
    parser.feed(content)
    return parser.forms


def _posted_field_names(content: str) -> set[str]:
    """The names of the fields inside the page's POST forms, whichever form."""
    return {name for _, names in _post_forms(content) for name in names}


@pytest.mark.django_db
def test_chat_page_is_served_in_english_and_in_french_with_a_question_form(
    client: Client,
) -> None:
    english_response = client.get("/chat/")
    french_response = client.get("/fr/chat/")

    assert english_response.status_code == 200
    assert english_response.headers.get("Content-Language") == "en"
    assert "question" in _posted_field_names(english_response.content.decode())
    assert french_response.status_code == 200
    assert french_response.headers.get("Content-Language") == "fr"
    assert "question" in _posted_field_names(french_response.content.decode())


class _FormInputs(HTMLParser):
    """Collect the attributes of each <input> inside the form with a given id."""

    def __init__(self, form_id: str) -> None:
        super().__init__()
        self.inputs: list[dict[str, str | None]] = []
        self._form_id = form_id
        self._in_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            self._in_form = attributes.get("id") == self._form_id
        elif self._in_form and tag == "input":
            self.inputs.append(attributes)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._in_form = False


def _form_inputs(content: str, form_id: str) -> list[dict[str, str | None]]:
    parser = _FormInputs(form_id)
    parser.feed(content)
    return parser.inputs


@pytest.mark.django_db
def test_chat_page_on_a_first_visit_holds_a_checked_use_history_checkbox(
    client: Client,
) -> None:
    response = client.get("/chat/")

    assert response.status_code == 200
    assert [
        ((attributes.get("type") or "").lower(), "checked" in attributes)
        for attributes in _form_inputs(response.content.decode(), "chat-form")
        if attributes.get("name") == "use_history"
    ] == [("checkbox", True)]


@pytest.mark.django_db
def test_chat_page_after_a_question_without_use_history_holds_it_unchecked(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_each_question_from(
        monkeypatch, {"How do I descale a kettle?": "Fill it with white vinegar."}
    )

    # A browser posts no use_history field when the box is unchecked.
    response = client.post(
        "/chat/", {"question": "How do I descale a kettle?"}, follow=True
    )

    assert response.status_code == 200
    assert [
        ((attributes.get("type") or "").lower(), "checked" in attributes)
        for attributes in _form_inputs(response.content.decode(), "chat-form")
        if attributes.get("name") == "use_history"
    ] == [("checkbox", False)]


@pytest.mark.django_db
def test_chat_page_after_questions_without_then_with_use_history_holds_it_checked(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_each_question_from(
        monkeypatch,
        {
            "How do I descale a kettle?": "Fill it with white vinegar.",
            "How long does it take?": "About an hour.",
        },
    )
    # A browser posts no use_history field when the box is unchecked.
    client.post("/chat/", {"question": "How do I descale a kettle?"})

    response = client.post(
        "/chat/",
        {"question": "How long does it take?", "use_history": "on"},
        follow=True,
    )

    assert response.status_code == 200
    assert [
        ((attributes.get("type") or "").lower(), "checked" in attributes)
        for attributes in _form_inputs(response.content.decode(), "chat-form")
        if attributes.get("name") == "use_history"
    ] == [("checkbox", True)]


@pytest.fixture
def chat_answer_kwargs() -> list[dict[str, object]]:
    """The keyword arguments of each call to the chat page's fake answer()."""
    return []


@pytest.fixture
def chat_questions(
    monkeypatch: pytest.MonkeyPatch, chat_answer_kwargs: list[dict[str, object]]
) -> list[str]:
    """Replace the chat page's answer() with a fake that records each question.

    The fake also records the keyword arguments of each call in
    chat_answer_kwargs, and finds nothing. It is set even while pages.views
    does not import answer() yet, so a test that expects no call can fail on
    its assertions.
    """
    questions: list[str] = []

    def fake_answer(question: str, **kwargs: object) -> None:
        questions.append(question)
        chat_answer_kwargs.append(kwargs)

    monkeypatch.setattr(CHAT_ANSWER, fake_answer, raising=False)
    return questions


def _without_csrf_tokens(content: str) -> str:
    """Blank the CSRF token values, which change with every rendering."""
    return re.sub(
        r'name="csrfmiddlewaretoken" value="[^"]*"',
        'name="csrfmiddlewaretoken" value=""',
        content,
    )


@pytest.mark.django_db
def test_chat_page_rejects_an_empty_question_without_answering_or_keeping_it(
    client: Client, chat_questions: list[str]
) -> None:
    page_before = client.get("/chat/")

    response = client.post("/chat/", {"question": ""})

    page_after = client.get("/chat/")
    assert 400 <= response.status_code < 500
    assert chat_questions == []
    assert _without_csrf_tokens(page_after.content.decode()) == _without_csrf_tokens(
        page_before.content.decode()
    )


@pytest.mark.django_db
def test_chat_page_rejects_a_whitespace_only_question_as_an_empty_one(
    client: Client, chat_questions: list[str]
) -> None:
    page_before = client.get("/chat/")

    response = client.post("/chat/", {"question": " \t\n  "})

    page_after = client.get("/chat/")
    assert 400 <= response.status_code < 500
    assert chat_questions == []
    assert _without_csrf_tokens(page_after.content.decode()) == _without_csrf_tokens(
        page_before.content.decode()
    )


@pytest.mark.django_db
def test_chat_page_asks_for_a_question_when_an_empty_one_is_posted(
    client: Client, chat_questions: list[str]
) -> None:
    # The message is the one the view defines, so this test does not fix the
    # wording itself; the plain chat page must not show it.
    question_required = escape(str(QUESTION_REQUIRED))
    page = client.get("/chat/")

    response = client.post("/chat/", {"question": ""})

    assert question_required
    assert question_required not in page.content.decode()
    content = response.content.decode()
    assert "question" in _posted_field_names(content)
    assert question_required in content


@pytest.mark.django_db
def test_chat_page_answers_in_english_as_an_anonymous_reader_with_ask_s_limits(
    client: Client,
    chat_questions: list[str],
    chat_answer_kwargs: list[dict[str, object]],
) -> None:
    client.post("/chat/", {"question": "How do I descale a kettle?"})

    assert chat_questions == ["How do I descale a kettle?"]
    assert chat_answer_kwargs == [
        {
            "language": "en",
            "permissions": frozenset(),
            "max_distance": MAX_DISTANCE,
            "limit": MAX_CHUNKS,
        }
    ]


@pytest.mark.django_db
def test_chat_page_answers_in_french_under_fr(
    client: Client,
    chat_questions: list[str],
    chat_answer_kwargs: list[dict[str, object]],
) -> None:
    client.post("/fr/chat/", {"question": "Comment détartrer une bouilloire ?"})

    assert chat_questions == ["Comment détartrer une bouilloire ?"]
    assert [kwargs["language"] for kwargs in chat_answer_kwargs] == ["fr"]


class _StartTags(HTMLParser):
    """Collect the names of the elements a response opens."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)


def _start_tags(content: str) -> set[str]:
    parser = _StartTags()
    parser.feed(content)
    return parser.tags


@pytest.mark.django_db
def test_chat_page_answers_a_fetch_post_with_the_new_exchange_alone(
    client: Client, chat_questions: list[str]
) -> None:
    response = client.post(
        "/chat/",
        {"question": "How do I descale a kettle?"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert _start_tags(content).isdisjoint({"html", "body", "nav"})
    assert "How do I descale a kettle?" in content


@pytest.mark.django_db
@pytest.mark.parametrize("chat_url", ["/chat/", "/fr/chat/"])
def test_chat_page_redirects_a_plain_post_to_the_chat_page_of_the_same_language(
    client: Client, chat_questions: list[str], chat_url: str
) -> None:
    response = client.post(chat_url, {"question": "How do I descale a kettle?"})

    assert response.status_code in (302, 303)
    assert response.headers["Location"] == chat_url


@pytest.mark.django_db
@pytest.mark.parametrize("chat_url", ["/chat/", "/fr/chat/"])
def test_chat_page_forbids_caches_from_storing_it(
    client: Client, chat_url: str
) -> None:
    # A stored copy would let the back button show exchanges cleared by a reset.
    response = client.get(chat_url)

    assert response.status_code == 200
    directives = {
        directive.strip().lower()
        for directive in response.headers.get("Cache-Control", "").split(",")
    }
    assert "no-store" in directives


RESET_AND_CHAT_URLS = [("/chat/reset/", "/chat/"), ("/fr/chat/reset/", "/fr/chat/")]


@pytest.fixture
def kettle_exchange(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    """Make the chat page's answer() reply to the kettle question; return both."""
    question, reply = "How do I descale a kettle?", "Fill it with white vinegar."
    answer_each_question_from(monkeypatch, {question: reply})
    return question, reply


@pytest.mark.django_db
@pytest.mark.parametrize(("reset_url", "chat_url"), RESET_AND_CHAT_URLS)
def test_chat_reset_redirects_to_the_chat_page_of_the_same_language(
    client: Client, reset_url: str, chat_url: str
) -> None:
    response = client.post(reset_url)

    assert response.status_code in (302, 303)
    assert response.headers["Location"] == chat_url


@pytest.mark.django_db
def test_chat_page_no_longer_shows_its_exchanges_after_a_reset(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
    }
    answer_each_question_from(monkeypatch, replies)
    client.post("/chat/", {"question": "How do I descale a kettle?"})
    before_reset = client.post(
        "/chat/", {"question": "Can a toaster take bagels?"}, follow=True
    )

    client.post("/chat/reset/")

    after_reset = client.get("/chat/")
    exchanged_texts = [text for exchange in replies.items() for text in exchange]
    assert [text in before_reset.content.decode() for text in exchanged_texts] == [
        True
    ] * 4
    assert after_reset.status_code == 200
    assert [text in after_reset.content.decode() for text in exchanged_texts] == [
        False
    ] * 4


@pytest.mark.django_db
def test_chat_reset_keeps_a_staff_user_logged_in_to_the_admin(
    admin_client: Client,
) -> None:
    admin_before = admin_client.get(reverse("admin:index"))

    admin_client.post(reverse("chat_reset"))

    admin_after = admin_client.get(reverse("admin:index"))
    assert admin_before.status_code == 200
    assert admin_after.status_code == 200


@pytest.mark.django_db
def test_chat_reset_of_a_session_with_exchanges_keeps_a_staff_user_logged_in(
    admin_client: Client, kettle_exchange: tuple[str, str]
) -> None:
    question, reply = kettle_exchange
    admin_client.post(reverse("chat"), {"question": question})
    chat_before = admin_client.get(reverse("chat")).content.decode()

    admin_client.post(reverse("chat_reset"))

    admin_after = admin_client.get(reverse("admin:index"))
    assert [question in chat_before, reply in chat_before] == [True, True]
    assert admin_after.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(("reset_url", "chat_url"), RESET_AND_CHAT_URLS)
def test_chat_reset_refuses_a_get_and_keeps_the_exchanges(
    client: Client, kettle_exchange: tuple[str, str], reset_url: str, chat_url: str
) -> None:
    question, reply = kettle_exchange
    client.post(chat_url, {"question": question})

    response = client.get(reset_url)

    page = client.get(chat_url).content.decode()
    assert response.status_code == 405
    assert [question in page, reply in page] == [True, True]


@pytest.mark.django_db
@pytest.mark.parametrize(("reset_url", "chat_url"), RESET_AND_CHAT_URLS)
def test_chat_reset_refuses_a_post_without_a_csrf_token_and_keeps_the_exchanges(
    kettle_exchange: tuple[str, str], reset_url: str, chat_url: str
) -> None:
    question, reply = kettle_exchange
    client = Client(enforce_csrf_checks=True)
    client.get(chat_url)
    csrf_token = client.cookies["csrftoken"].value
    client.post(chat_url, {"question": question, "csrfmiddlewaretoken": csrf_token})

    response = client.post(reset_url)

    page = client.get(chat_url).content.decode()
    assert response.status_code == 403
    assert [question in page, reply in page] == [True, True]


@pytest.mark.django_db
@pytest.mark.parametrize(("reset_url", "chat_url"), RESET_AND_CHAT_URLS)
def test_chat_page_with_exchanges_holds_a_csrf_protected_post_form_to_its_reset(
    client: Client, kettle_exchange: tuple[str, str], reset_url: str, chat_url: str
) -> None:
    question, _ = kettle_exchange
    client.post(chat_url, {"question": question})

    response = client.get(chat_url)

    assert response.status_code == 200
    content = response.content.decode()
    assert question in content
    assert [
        "csrfmiddlewaretoken" in names
        for action, names in _post_forms(content)
        if action == reset_url
    ] == [True]


@pytest.mark.django_db
def test_chat_page_shows_the_question_and_the_answer_text_after_a_plain_post(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Fill it with white vinegar and leave it overnight.",
            chunks=(
                RetrievedChunk(
                    text="Vinegar dissolves limescale overnight.",
                    title="Descaling a kettle",
                    url="/blog/1/",
                    source_key="blog.article:1",
                    distance=0.1,
                ),
            ),
            search_question="How do I descale a kettle?",
        ),
    )

    response = client.post(
        "/chat/", {"question": "How do I descale a kettle?"}, follow=True
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "How do I descale a kettle?" in content
    assert "Fill it with white vinegar and leave it overnight." in content


@pytest.mark.django_db
def test_chat_page_shows_two_plain_post_exchanges_oldest_first_each_answered_alone(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
    }
    questions = answer_each_question_from(monkeypatch, replies)

    client.post("/chat/", {"question": "How do I descale a kettle?"}, follow=True)
    response = client.post(
        "/chat/", {"question": "Can a toaster take bagels?"}, follow=True
    )

    assert response.status_code == 200
    assert questions == list(replies)
    content = response.content.decode()
    shown_in_order = [text for exchange in replies.items() for text in exchange]
    assert [text in content for text in shown_in_order] == [True] * 4
    _assert_in_order(content, shown_in_order)


@pytest.mark.django_db
def test_chat_page_answers_with_use_history_on_with_its_earlier_exchange_as_history(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)

    client.post("/chat/", {"question": "How do I descale a kettle?"})
    client.post("/chat/", {"question": "How long does it take?", "use_history": "on"})

    assert len(histories) == 2
    assert list(histories[1]) == [
        Exchange(
            question="How do I descale a kettle?",
            answer="Fill it with white vinegar overnight.",
        )
    ]


@pytest.mark.django_db
def test_chat_page_answers_with_use_history_on_with_both_earlier_exchanges_oldest_first(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
        "Which of them is cheaper?": "The kettle.",
    }
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(text=replies[question], chunks=(), search_question=question)

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)

    client.post("/chat/", {"question": "How do I descale a kettle?"})
    client.post("/chat/", {"question": "Can a toaster take bagels?"})
    client.post(
        "/chat/", {"question": "Which of them is cheaper?", "use_history": "on"}
    )

    assert len(histories) == 3
    assert list(histories[2]) == [
        Exchange(
            question="How do I descale a kettle?",
            answer="Fill it with white vinegar overnight.",
        ),
        Exchange(
            question="Can a toaster take bagels?",
            answer="Yes, use the bagel setting.",
        ),
    ]


@pytest.mark.django_db
def test_chat_page_answers_with_use_history_on_with_only_the_last_five_exchanges(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    earlier = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
        "Is the blender dishwasher safe?": "Only its jar.",
        "Does the iron have a steam boost?": "Yes, press the boost button.",
        "How loud is the fan?": "About 40 decibels.",
        "Can the oven grill?": "Yes, it has a top grill.",
    }
    replies = {**earlier, "Which of them is cheaper?": "The kettle."}
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(text=replies[question], chunks=(), search_question=question)

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)

    for question in earlier:
        client.post("/chat/", {"question": question})
    client.post(
        "/chat/", {"question": "Which of them is cheaper?", "use_history": "on"}
    )

    assert len(histories) == 7
    assert list(histories[6]) == [
        Exchange(question=question, answer=reply)
        for question, reply in list(earlier.items())[1:]
    ]


@pytest.mark.django_db
def test_chat_page_passes_a_nothing_close_enough_exchange_in_history_as_shown(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The ask command's message when answer() finds nothing is the reference,
    # so this test does not fix the wording itself.
    nothing_close_enough = _ask_command_output_when_nothing_is_found(monkeypatch)
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer | None:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        if question == "How do I descale a kettle?":
            return None
        return Answer(text="The kettle.", chunks=(), search_question=question)

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)

    client.post("/chat/", {"question": "How do I descale a kettle?"})
    client.post("/chat/", {"question": "How long does it take?", "use_history": "on"})

    assert len(histories) == 2
    assert list(histories[1]) == [
        Exchange(question="How do I descale a kettle?", answer=nothing_close_enough)
    ]


@pytest.mark.django_db
def test_chat_page_answers_with_use_history_on_with_no_history_after_a_reset(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    client.post("/chat/", {"question": "How do I descale a kettle?"})

    client.post("/chat/reset/")
    client.post("/chat/", {"question": "How long does it take?", "use_history": "on"})

    assert len(histories) == 2
    assert list(histories[1]) == []


@pytest.mark.django_db
def test_chat_page_answers_without_use_history_with_no_history_after_an_exchange(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    client.post("/chat/", {"question": "How do I descale a kettle?"})

    # A browser posts no use_history field when the box is unchecked.
    client.post("/chat/", {"question": "How long does it take?"})

    assert len(histories) == 2
    assert list(histories[1]) == []


@pytest.mark.django_db
def test_french_chat_page_answers_with_use_history_on_without_the_english_exchanges(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Comment détartrer une bouilloire ?": "Remplissez-la de vinaigre blanc.",
        "Combien de temps faut-il ?": "Une nuit.",
    }
    histories: list[Sequence[Exchange]] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        history = kwargs.get("history", ())
        assert isinstance(history, Sequence)
        histories.append(history)
        return Answer(text=replies[question], chunks=(), search_question=question)

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    client.post("/chat/", {"question": "How do I descale a kettle?"})
    client.post("/fr/chat/", {"question": "Comment détartrer une bouilloire ?"})

    client.post(
        "/fr/chat/", {"question": "Combien de temps faut-il ?", "use_history": "on"}
    )

    assert len(histories) == 3
    assert list(histories[2]) == [
        Exchange(
            question="Comment détartrer une bouilloire ?",
            answer="Remplissez-la de vinaigre blanc.",
        )
    ]


@pytest.mark.django_db
def test_chat_page_does_not_show_one_visitor_s_exchanges_to_another_visitor(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question="How do I descale a kettle?",
        ),
    )
    first_visit = client.post(
        "/chat/", {"question": "How do I descale a kettle?"}, follow=True
    )

    second_visit = Client().get("/chat/")

    assert "How do I descale a kettle?" in first_visit.content.decode()
    assert second_visit.status_code == 200
    content = second_visit.content.decode()
    assert "How do I descale a kettle?" not in content
    assert "Fill it with white vinegar overnight." not in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("chat_url", "exchange", "other_chat_url", "other_exchange"),
    [
        pytest.param(
            "/chat/",
            ("How do I descale a kettle?", "Fill it with white vinegar overnight."),
            "/fr/chat/",
            ("Comment détartrer une bouilloire ?", "Remplissez-la de vinaigre blanc."),
            id="french-exchange-on-english-page",
        ),
        pytest.param(
            "/fr/chat/",
            ("Comment détartrer une bouilloire ?", "Remplissez-la de vinaigre blanc."),
            "/chat/",
            ("How do I descale a kettle?", "Fill it with white vinegar overnight."),
            id="english-exchange-on-french-page",
        ),
    ],
)
def test_chat_page_does_not_show_an_exchange_asked_in_the_other_language(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    chat_url: str,
    exchange: tuple[str, str],
    other_chat_url: str,
    other_exchange: tuple[str, str],
) -> None:
    question, reply = exchange
    other_question, other_reply = other_exchange
    answer_each_question_from(
        monkeypatch, {question: reply, other_question: other_reply}
    )

    client.post(chat_url, {"question": question})
    client.post(other_chat_url, {"question": other_question})
    response = client.get(chat_url)

    assert response.status_code == 200
    content = response.content.decode()
    assert [
        text in content for text in (question, reply, other_question, other_reply)
    ] == [True, True, False, False]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("reset_url", "reset_chat_url", "exchange", "kept_chat_url", "kept_exchange"),
    [
        pytest.param(
            "/fr/chat/reset/",
            "/fr/chat/",
            ("Comment détartrer une bouilloire ?", "Remplissez-la de vinaigre blanc."),
            "/chat/",
            ("How do I descale a kettle?", "Fill it with white vinegar overnight."),
            id="french-reset-keeps-english-exchanges",
        ),
        pytest.param(
            "/chat/reset/",
            "/chat/",
            ("How do I descale a kettle?", "Fill it with white vinegar overnight."),
            "/fr/chat/",
            ("Comment détartrer une bouilloire ?", "Remplissez-la de vinaigre blanc."),
            id="english-reset-keeps-french-exchanges",
        ),
    ],
)
def test_chat_reset_keeps_the_exchanges_of_the_other_language(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    reset_url: str,
    reset_chat_url: str,
    exchange: tuple[str, str],
    kept_chat_url: str,
    kept_exchange: tuple[str, str],
) -> None:
    question, reply = exchange
    kept_question, kept_reply = kept_exchange
    answer_each_question_from(monkeypatch, {question: reply, kept_question: kept_reply})
    client.post(reset_chat_url, {"question": question})
    client.post(kept_chat_url, {"question": kept_question})

    client.post(reset_url)

    reset_page = client.get(reset_chat_url).content.decode()
    kept_page = client.get(kept_chat_url).content.decode()
    assert [question in reset_page, reply in reset_page] == [False, False]
    assert [kept_question in kept_page, kept_reply in kept_page] == [True, True]


class _Links(HTMLParser):
    """Collect each link of a response as (target, text), in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def _links(content: str) -> list[tuple[str, str]]:
    parser = _Links()
    parser.feed(content)
    return parser.links


@pytest.mark.django_db
def test_chat_page_shows_the_answer_s_sources_in_order_linked_after_a_plain_post(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def chunk(title: str, url: str, source_key: str, distance: float) -> RetrievedChunk:
        return RetrievedChunk(
            text=f"An extract of {title}.",
            title=title,
            url=url,
            source_key=source_key,
            distance=distance,
        )

    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Use the bagel setting, then descale with white vinegar.",
            chunks=(
                chunk("Toasting bagels", "/blog/2/", "blog.article:2", 0.1),
                chunk("Descaling a kettle", "/blog/1/", "blog.article:1", 0.2),
                chunk("Toasting bagels", "/blog/2/", "blog.article:2", 0.3),
            ),
            search_question="How do I toast bagels and descale?",
        ),
    )

    response = client.post(
        "/chat/", {"question": "How do I toast bagels and descale?"}, follow=True
    )

    assert response.status_code == 200
    source_urls = {"/blog/1/", "/blog/2/"}
    source_links = [
        (href, text)
        for href, text in _links(response.content.decode())
        if href in source_urls
    ]
    assert source_links == [
        ("/blog/2/", "Toasting bagels"),
        ("/blog/1/", "Descaling a kettle"),
    ]


@pytest.mark.django_db
def test_chat_page_shows_a_source_without_url_as_its_title_unlinked_after_a_plain_post(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Orders arrive within two working days.",
            chunks=(
                RetrievedChunk(
                    text="We ship every order within two working days.",
                    title="Delivery terms",
                    url="",
                    source_key="pages.accordionitem:7",
                    distance=0.1,
                ),
            ),
            search_question="When will my order arrive?",
        ),
    )

    response = client.post(
        "/chat/", {"question": "When will my order arrive?"}, follow=True
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Delivery terms" in content
    assert [
        (href, text)
        for href, text in _links(content)
        if href == "" or text == "Delivery terms"
    ] == []


_VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"}
    | {"source", "track", "wbr"}
)


class _TextsByAttribute(HTMLParser):
    """Collect the text of each element with a given attribute value, in order."""

    def __init__(self, attribute: str, value: str) -> None:
        super().__init__()
        self.texts: list[str] = []
        self._attribute = attribute
        self._value = value
        self._depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID_ELEMENTS:
            return
        if self._depth:
            self._depth += 1
        elif dict(attrs).get(self._attribute) == self._value:
            self._depth = 1
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_ELEMENTS or not self._depth:
            return
        self._depth -= 1
        if not self._depth:
            self.texts.append(" ".join("".join(self._text).split()))


def _texts_by_attribute(content: str, attribute: str, value: str) -> list[str]:
    parser = _TextsByAttribute(attribute, value)
    parser.feed(content)
    return parser.texts


@pytest.mark.django_db
def test_chat_page_shows_the_retrieved_extracts_nearest_first_with_their_titles(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Answer.chunks are documented nearest first: the page keeps their order,
    # which neither groups them by document nor sorts them by title or text.
    retrieved = (
        ("Toasting bagels", "Use the bagel setting for a soft top."),
        ("Descaling a kettle", "Vinegar dissolves limescale overnight."),
        ("Toasting bagels", "A bagel takes longer than a slice of bread."),
    )

    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Use the bagel setting, then descale with white vinegar.",
            chunks=tuple(
                RetrievedChunk(
                    text=text,
                    title=title,
                    url=f"/blog/{len(title)}/",
                    source_key=f"blog.article:{len(title)}",
                    distance=0.1 * (rank + 1),
                )
                for rank, (title, text) in enumerate(retrieved)
            ),
            search_question="How do I toast bagels and descale?",
        ),
    )

    response = client.post(
        "/chat/", {"question": "How do I toast bagels and descale?"}, follow=True
    )

    assert response.status_code == 200
    extracts = _texts_by_attribute(response.content.decode(), "data-testid", "extract")
    assert [
        (title in extract, text in extract)
        for extract, (title, text) in zip(extracts, retrieved, strict=False)
    ] == [(True, True)] * len(retrieved)
    assert len(extracts) == len(retrieved)


ASK_ANSWER = "assistant.management.commands.ask.answer"


def _ask_command_output_when_nothing_is_found(monkeypatch: pytest.MonkeyPatch) -> str:
    """What the ask command prints when its answer() finds nothing."""
    monkeypatch.setattr(ASK_ANSWER, lambda question, **kwargs: None)
    ask_output = StringIO()
    call_command("ask", "How do I descale a kettle?", stdout=ask_output)
    return ask_output.getvalue().strip()


@pytest.mark.django_db
def test_chat_page_says_nothing_indexed_is_close_enough_after_a_plain_post(
    client: Client, chat_questions: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The ask command's message when answer() finds nothing is the reference,
    # so this test does not fix the wording itself.
    nothing_close_enough = _ask_command_output_when_nothing_is_found(monkeypatch)

    response = client.post(
        "/chat/", {"question": "How do I descale a kettle?"}, follow=True
    )

    assert response.status_code == 200
    assert escape(nothing_close_enough) in response.content.decode()


@pytest.mark.django_db
def test_chat_page_says_nothing_indexed_is_close_enough_in_french_under_fr(
    client: Client, chat_questions: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The reference is the ask command's English message and its translation
    # in the project's French catalog, so this test does not fix the wording.
    with override("en"):
        english_message = _ask_command_output_when_nothing_is_found(monkeypatch)
    with override("fr"):
        french_message = gettext(english_message)

    response = client.post(
        "/fr/chat/", {"question": "Comment détartrer une bouilloire ?"}, follow=True
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert escape(english_message) not in content
    assert escape(french_message) in content


@pytest.mark.django_db
def test_chat_page_says_the_assistant_is_unavailable_when_the_backend_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Each question meets a different httpx failure: the exchanges shown all
    # say the same thing, which is neither the error's own detail nor the
    # "nothing close enough" message, so the wording itself stays free.
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    failures: dict[str, httpx.HTTPError] = {
        "How do I descale a kettle?": httpx.ConnectError(
            "All connection attempts failed", request=request
        ),
        "Can a toaster take bagels?": httpx.HTTPStatusError(
            "Server error '500 Internal Server Error'",
            request=request,
            response=httpx.Response(500, request=request),
        ),
        "When will my order arrive?": httpx.ReadTimeout("timed out", request=request),
    }

    def fake_answer(question: str, **kwargs: object) -> Answer:
        raise failures[question]

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    client = Client(raise_request_exception=False)

    posts = [client.post("/chat/", {"question": question}) for question in failures]
    page = client.get("/chat/")

    assert {post.status_code for post in posts} <= {302, 303}
    assert page.status_code == 200
    exchanges = page.context["exchanges"]
    assert [exchange["question"] for exchange in exchanges] == list(failures)
    shown = {exchange["text"] for exchange in exchanges}
    assert len(shown) == 1
    (unavailable,) = shown
    assert unavailable
    assert unavailable != str(NOTHING_CLOSE_ENOUGH)
    assert escape(unavailable) in page.content.decode()


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


def _create_content_and_get_every_view_url(language: str) -> dict[str, str]:
    """Create one product, article and page in language; map each view to its URL."""
    product = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=Category.objects.create(name="Kitchen"),
        language=language,
    )
    article = Article.objects.create(
        title="Descaling a kettle",
        body="Fill it with white vinegar and leave it overnight.",
        language=language,
    )
    page = Page.objects.create(title="About us", slug="about", language=language)
    with override(language):
        return {
            "home": reverse("home"),
            "chat": reverse("chat"),
            "product_list": reverse("product_list"),
            "product_detail": product.get_absolute_url(),
            "page_detail": page.get_absolute_url(),
            "article_list": reverse("article_list"),
            "article_detail": article.get_absolute_url(),
        }


@pytest.mark.django_db
@pytest.mark.parametrize(("language", "other_home"), [("en", "/fr/"), ("fr", "/")])
@pytest.mark.parametrize(
    "view",
    [
        "home",
        "product_list",
        "product_detail",
        "page_detail",
        "article_list",
        "article_detail",
    ],
)
def test_every_view_links_to_the_home_of_the_other_language(
    client: Client,
    rag_store: DocumentStore,
    view: str,
    language: str,
    other_home: str,
) -> None:
    urls = _create_content_and_get_every_view_url(language)

    response = client.get(urls[view])

    assert response.status_code == 200
    assert f'href="{other_home}"' in response.content.decode()


class _NavLinks(HTMLParser):
    """Collect the targets of the links inside the page's <nav>."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self._in_nav = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "nav":
            self._in_nav = True
        elif self._in_nav and tag == "a":
            self.hrefs.append(dict(attrs).get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav":
            self._in_nav = False


def _nav_links(content: str) -> list[str]:
    parser = _NavLinks()
    parser.feed(content)
    return parser.hrefs


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "chat_url"), [("en", "/chat/"), ("fr", "/fr/chat/")]
)
@pytest.mark.parametrize(
    "view",
    [
        "home",
        "chat",
        "product_list",
        "product_detail",
        "page_detail",
        "article_list",
        "article_detail",
    ],
)
def test_every_view_nav_links_to_the_chat_page_of_the_active_language(
    client: Client,
    rag_store: DocumentStore,
    view: str,
    language: str,
    chat_url: str,
) -> None:
    urls = _create_content_and_get_every_view_url(language)

    response = client.get(urls[view])

    assert response.status_code == 200
    assert chat_url in _nav_links(response.content.decode())


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


def _create_an_english_and_a_french_product() -> tuple[Product, Product]:
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
    return english, french


@pytest.mark.django_db
def test_product_list_shows_only_the_products_of_the_active_language(
    client: Client, rag_store: DocumentStore
) -> None:
    english, french = _create_an_english_and_a_french_product()

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
    english, french = _create_an_english_and_a_french_product()

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
def test_page_view_holds_each_accordion_item_under_its_document_url_fragment(
    client: Client, rag_store: DocumentStore
) -> None:
    page = Page.objects.create(title="FAQ", slug="faq")
    shipping = AccordionItem.objects.create(
        page=page, title="Shipping", body="We ship within two days."
    )
    returns = AccordionItem.objects.create(
        page=page, title="Returns", body="Returns are free for 30 days."
    )
    call_command("sync_model_rag")

    response = client.get(page.get_absolute_url())

    assert response.status_code == 200
    content = response.content.decode()
    for item, other in ((shipping, returns), (returns, shipping)):
        [document] = rag_store[f"pages.accordionitem:{item.pk}"]
        fragment = urlsplit(document.url).fragment
        needles = (item.title, item.body, other.body)
        assert [
            [needle in text for needle in needles]
            for text in _texts_by_attribute(content, "id", fragment)
        ] == [[True, True, False]]


@pytest.mark.django_db
def test_page_view_does_not_find_a_page_of_the_other_language(
    client: Client, rag_store: DocumentStore
) -> None:
    Page.objects.create(title="Delivery", slug="delivery", language="en")
    Page.objects.create(title="Livraison", slug="livraison", language="fr")

    french_under_root = client.get("/pages/livraison/")
    english_under_fr = client.get("/fr/pages/delivery/")

    assert french_under_root.status_code == 404
    assert english_under_fr.status_code == 404


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
