import pytest
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks

from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import DocumentStore


@pytest.mark.django_db
def test_editing_a_page_updates_the_documents_of_its_blocks(
    rag_store: DocumentStore,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        page = Page.objects.create(title="FAQ", slug="faq")
        text_block = TextPlugin.objects.create(page=page, body="We make kettles.")
        accordion_item = AccordionItem.objects.create(
            page=page, title="Shipping", body="We ship within two days."
        )

    with django_capture_on_commit_callbacks(execute=True):
        page.title = "Help"
        page.slug = "help"
        page.save()

    [text_document] = rag_store[f"pages.textplugin:{text_block.pk}"]
    [accordion_document] = rag_store[f"pages.accordionitem:{accordion_item.pk}"]
    assert text_document.title == "Help"
    assert text_document.url == "/pages/help/"
    assert accordion_document.title == "Help — Shipping"
    assert accordion_document.url == "/pages/help/"


@pytest.mark.django_db
def test_deleting_a_page_removes_the_documents_of_its_blocks(
    rag_store: DocumentStore,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        page = Page.objects.create(title="FAQ", slug="faq")
        text_block = TextPlugin.objects.create(page=page, body="We make kettles.")
        accordion_item = AccordionItem.objects.create(
            page=page, title="Shipping", body="We ship within two days."
        )
        other_page = Page.objects.create(title="About", slug="about")
        other_text_block = TextPlugin.objects.create(
            page=other_page, body="We are a small team."
        )

    with django_capture_on_commit_callbacks(execute=True):
        page.delete()

    assert f"pages.textplugin:{text_block.pk}" not in rag_store
    assert f"pages.accordionitem:{accordion_item.pk}" not in rag_store
    assert f"pages.textplugin:{other_text_block.pk}" in rag_store
