import pytest
from django.core.management import call_command

from pages.models import AccordionItem, Page, TextPlugin
from tests.conftest import DocumentStore


@pytest.mark.django_db
def test_sync_gives_each_text_block_of_a_page_its_own_document(
    rag_store: DocumentStore,
) -> None:
    page = Page.objects.create(title="About us", slug="about")
    first = TextPlugin.objects.create(page=page, body="We make kettles.")
    second = TextPlugin.objects.create(page=page, body="Since 1998.")

    call_command("sync_model_rag")

    [first_document] = rag_store[f"pages.textplugin:{first.pk}"]
    [second_document] = rag_store[f"pages.textplugin:{second.pk}"]
    assert first_document.title == "About us"
    assert first_document.text == "We make kettles."
    assert first_document.url == "/pages/about/"
    assert second_document.title == "About us"
    assert second_document.text == "Since 1998."
    assert second_document.url == "/pages/about/"


@pytest.mark.django_db
def test_sync_gives_no_document_for_an_empty_or_blank_text_block(
    rag_store: DocumentStore,
) -> None:
    page = Page.objects.create(title="About us", slug="about")
    empty = TextPlugin.objects.create(page=page, body="")
    blank = TextPlugin.objects.create(page=page, body="  \n\t ")
    filled = TextPlugin.objects.create(page=page, body="We make kettles.")

    call_command("sync_model_rag")

    assert f"pages.textplugin:{empty.pk}" not in rag_store
    assert f"pages.textplugin:{blank.pk}" not in rag_store
    [filled_document] = rag_store[f"pages.textplugin:{filled.pk}"]
    assert filled_document.text == "We make kettles."


@pytest.mark.django_db
def test_sync_gives_each_accordion_item_of_a_page_its_own_document(
    rag_store: DocumentStore,
) -> None:
    page = Page.objects.create(title="FAQ", slug="faq")
    first = AccordionItem.objects.create(
        page=page, title="Shipping", body="We ship within two days."
    )
    second = AccordionItem.objects.create(
        page=page, title="Returns", body="Returns are free for 30 days."
    )

    call_command("sync_model_rag")

    [first_document] = rag_store[f"pages.accordionitem:{first.pk}"]
    [second_document] = rag_store[f"pages.accordionitem:{second.pk}"]
    assert first_document.title == "FAQ — Shipping"
    assert first_document.text == "Shipping\n\nWe ship within two days."
    assert first_document.url == "/pages/faq/"
    assert second_document.title == "FAQ — Returns"
    assert second_document.text == "Returns\n\nReturns are free for 30 days."
    assert second_document.url == "/pages/faq/"
