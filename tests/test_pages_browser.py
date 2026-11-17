import pytest
from django.core.management import call_command
from playwright.sync_api import Page as BrowserPage
from playwright.sync_api import expect
from pytest_django.live_server_helper import LiveServer

from pages.models import AccordionItem, Page
from tests.rag_output import DocumentStore


@pytest.mark.django_db
@pytest.mark.usefixtures("_allow_the_orm_beside_playwright")
def test_page_opened_at_an_accordion_item_document_url_shows_that_item_open(
    live_server: LiveServer, page: BrowserPage, rag_store: DocumentStore
) -> None:
    faq = Page.objects.create(title="FAQ", slug="faq")
    AccordionItem.objects.create(
        page=faq, title="Shipping", body="We ship within two days."
    )
    returns = AccordionItem.objects.create(
        page=faq, title="Returns", body="Returns are free for 30 days."
    )
    call_command("sync_model_rag")
    [document] = rag_store[f"pages.accordionitem:{returns.pk}"]

    page.goto(f"{live_server.url}{document.url}")

    expect(page.get_by_text("Returns are free for 30 days.")).to_be_visible()
    expect(page.get_by_text("We ship within two days.")).to_be_hidden()
