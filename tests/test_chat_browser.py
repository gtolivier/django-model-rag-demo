import threading

import pytest
from django_minimal_rag.answering import Answer
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.chat_answers import (
    CHAT_ANSWER,
    answer_each_question_from,
    answer_every_question_with,
)

QUESTION_FIELD = '[name="question"]'
RESET_BUTTON = 'form[action$="/chat/reset/"] [type="submit"]'


def _ask(page: Page, question: str) -> None:
    """Type question in the chat page's question field and submit it."""
    question_field = page.locator(QUESTION_FIELD)
    question_field.fill(question)
    question_field.press("Enter")


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_adds_a_submitted_exchange_below_the_previous_ones_without_reloading(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
    }
    answer_each_question_from(monkeypatch, replies)
    page.goto(f"{live_server.url}/chat/")
    _ask(page, "How do I descale a kettle?")
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()
    page.evaluate("window.chatPageMarker = 'still the same page'")

    _ask(page, "Can a toaster take bagels?")

    expect(page.get_by_text("Yes, use the bagel setting.")).to_be_visible()
    assert page.evaluate("window.chatPageMarker") == "still the same page"
    shown = page.locator("body").inner_text()
    shown_in_order = [text for exchange in replies.items() for text in exchange]
    positions = [shown.find(text) for text in shown_in_order]
    assert -1 not in positions
    assert positions == sorted(positions)


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_still_shows_an_exchange_asked_without_reloading_after_a_reload(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question="How do I descale a kettle?",
        ),
    )
    page.goto(f"{live_server.url}/chat/")
    page.evaluate("window.chatPageMarker = 'still the same page'")
    _ask(page, "How do I descale a kettle?")
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()
    assert page.evaluate("window.chatPageMarker") == "still the same page"

    page.reload()

    expect(page.get_by_text("How do I descale a kettle?")).to_be_visible()
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_offers_a_reset_once_the_first_answer_is_added_without_reloading(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question="How do I descale a kettle?",
        ),
    )
    reset_button = page.locator(RESET_BUTTON)
    page.goto(f"{live_server.url}/chat/")
    expect(reset_button).to_have_count(0)
    page.evaluate("window.chatPageMarker = 'still the same page'")
    _ask(page, "How do I descale a kettle?")
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()

    expect(reset_button).to_be_visible()
    assert page.evaluate("window.chatPageMarker") == "still the same page"

    reset_button.click()

    expect(page.locator(QUESTION_FIELD)).to_be_visible()
    expect(page.get_by_text("How do I descale a kettle?")).to_have_count(0)
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_have_count(0)
    expect(reset_button).to_have_count(0)


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_disables_the_reset_while_a_question_is_being_answered(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    second_answer_may_go = threading.Event()

    def fake_answer(question: str, **kwargs: object) -> Answer:
        if question == "Can a toaster take bagels?":
            second_answer_may_go.wait(timeout=30)
            return Answer(
                text="Yes, use the bagel setting.", chunks=(), search_question=question
            )
        return Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    reset_button = page.locator(RESET_BUTTON)
    page.goto(f"{live_server.url}/chat/")
    _ask(page, "How do I descale a kettle?")
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()
    expect(reset_button).to_be_enabled()

    try:
        _ask(page, "Can a toaster take bagels?")

        expect(reset_button).to_be_disabled()
    finally:
        second_answer_may_go.set()

    expect(page.get_by_text("Yes, use the bagel setting.")).to_be_visible()
    expect(reset_button).to_be_enabled()


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_makes_the_question_read_only_while_it_is_being_answered(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_may_go = threading.Event()
    questions_received: list[str] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        questions_received.append(question)
        answer_may_go.wait(timeout=30)
        return Answer(
            text="Fill it with white vinegar overnight.",
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    question_field = page.locator(QUESTION_FIELD)
    page.goto(f"{live_server.url}/chat/")
    expect(question_field).to_be_editable()

    try:
        _ask(page, "How do I descale a kettle?")

        expect(question_field).not_to_be_editable()
        expect(question_field).to_be_enabled()
    finally:
        answer_may_go.set()

    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()
    expect(question_field).to_be_editable()
    assert questions_received == ["How do I descale a kettle?"]


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_reloads_when_it_is_restored_from_the_back_forward_cache(
    live_server: LiveServer, page: Page
) -> None:
    page_marker = page.locator("body[data-chat-page-marker]")
    page.goto(f"{live_server.url}/chat/")
    page.evaluate("document.body.dataset.chatPageMarker = 'still the same page'")
    expect(page_marker).to_have_count(1)

    page.evaluate(
        "window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))"
    )

    expect(page_marker).to_have_count(0)
    expect(page.locator(QUESTION_FIELD)).to_be_visible()


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
@pytest.mark.browser_context_args(java_script_enabled=False)
def test_chat_page_without_javascript_offers_a_reset_only_for_its_own_exchanges(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer_every_question_with(
        monkeypatch,
        Answer(
            text="Remplissez-la de vinaigre blanc.",
            chunks=(),
            search_question="Comment détartrer une bouilloire ?",
        ),
    )
    reset_button = page.locator(RESET_BUTTON)

    page.goto(f"{live_server.url}/chat/")
    expect(page.locator(QUESTION_FIELD)).to_be_visible()
    expect(reset_button).to_have_count(0)

    page.goto(f"{live_server.url}/fr/chat/")
    _ask(page, "Comment détartrer une bouilloire ?")
    expect(page.get_by_text("Remplissez-la de vinaigre blanc.")).to_be_visible()
    expect(reset_button).to_be_visible()

    page.goto(f"{live_server.url}/chat/")
    expect(page.locator(QUESTION_FIELD)).to_be_visible()
    expect(reset_button).to_have_count(0)
