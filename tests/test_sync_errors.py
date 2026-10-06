import logging
from decimal import Decimal

import pytest
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import OutputUnavailableError


def _logged_output_errors(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == "django_model_rag"
        and record.levelno == logging.ERROR
        and record.exc_info is not None
        and isinstance(record.exc_info[1], OutputUnavailableError)
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("rag_store")
def test_an_output_error_at_the_commit_of_a_page_or_category_edit_is_logged_and_does_not_break_the_save(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        category = Category.objects.create(name="Kitchen")
        Product.objects.create(
            name="Kettle",
            description="Boils a litre of water in two minutes.",
            price=Decimal("29.90"),
            category=category,
        )
        page = Page.objects.create(title="FAQ", slug="faq")
        TextPlugin.objects.create(page=page, body="We make kettles.")
        AccordionItem.objects.create(
            page=page, title="Shipping", body="We ship within two days."
        )
    settings.MODEL_RAG_OUTPUT = {"BACKEND": "tests.rag_output.FailingOutput"}
    caplog.set_level(logging.ERROR, logger="django_model_rag")

    with django_capture_on_commit_callbacks(execute=True):
        category.name = "Cookware"
        category.save()
    category_errors = _logged_output_errors(caplog)
    caplog.clear()
    with django_capture_on_commit_callbacks(execute=True):
        page.title = "Help"
        page.save()
    page_errors = _logged_output_errors(caplog)

    assert category_errors
    assert page_errors
    assert Category.objects.get(pk=category.pk).name == "Cookware"
    assert Page.objects.get(pk=page.pk).title == "Help"
