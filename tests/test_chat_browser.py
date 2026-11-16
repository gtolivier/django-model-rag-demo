from collections.abc import Iterator

import pytest
from django_minimal_rag.answering import Answer
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

CHAT_ANSWER = "pages.views.answer"


@pytest.fixture(scope="session")
def _allow_the_orm_beside_playwright() -> Iterator[None]:
    """Let Django's ORM run while Playwright's event loop is running.

    Playwright's sync API keeps an event loop running in the test thread for
    the whole session, and Django refuses ORM calls from such a thread: the
    database setup and teardown of a live_server test would fail. Session
    scoped, so it still holds when the test database is flushed.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_chat_page_adds_a_submitted_exchange_below_the_previous_ones_without_reloading(
    live_server: LiveServer, page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = {
        "How do I descale a kettle?": "Fill it with white vinegar overnight.",
        "Can a toaster take bagels?": "Yes, use the bagel setting.",
    }

    def fake_answer(question: str, **kwargs: object) -> Answer:
        return Answer(text=replies.get(question, "An unexpected question."), chunks=())

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    page.goto(f"{live_server.url}/chat/")
    question_field = page.locator('[name="question"]')
    question_field.fill("How do I descale a kettle?")
    question_field.press("Enter")
    expect(page.get_by_text("Fill it with white vinegar overnight.")).to_be_visible()
    page.evaluate("window.chatPageMarker = 'still the same page'")

    question_field.fill("Can a toaster take bagels?")
    question_field.press("Enter")

    expect(page.get_by_text("Yes, use the bagel setting.")).to_be_visible()
    assert page.evaluate("window.chatPageMarker") == "still the same page"
    shown = page.locator("body").inner_text()
    shown_in_order = [text for exchange in replies.items() for text in exchange]
    positions = [shown.find(text) for text in shown_in_order]
    assert -1 not in positions
    assert positions == sorted(positions)
