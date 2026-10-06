import logging
from decimal import Decimal

import pytest
from django.core.exceptions import ImproperlyConfigured
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from catalog.models import Category, Product
from pages.models import AccordionItem, Page, TextPlugin
from tests.rag_output import OutputUnavailableError


def _logged_output_errors(
    caplog: pytest.LogCaptureFixture,
    error_type: type[BaseException] = OutputUnavailableError,
) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == "django_model_rag"
        and record.levelno == logging.ERROR
        and record.exc_info is not None
        and isinstance(record.exc_info[1], error_type)
    ]


def _category_and_page_with_dependents(
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> tuple[Category, Page]:
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
    return category, page


def _errors_logged_by_editing_the_category_then_the_page(
    category: Category,
    page: Page,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
    error_type: type[BaseException] = OutputUnavailableError,
) -> tuple[list[logging.LogRecord], list[logging.LogRecord]]:
    """Rename the category to Cookware, then retitle the page Help, each in
    a transaction that commits; give the errors each edit logged."""
    caplog.set_level(logging.ERROR, logger="django_model_rag")
    with django_capture_on_commit_callbacks(execute=True):
        category.name = "Cookware"
        category.save()
    category_errors = _logged_output_errors(caplog, error_type)
    caplog.clear()
    with django_capture_on_commit_callbacks(execute=True):
        page.title = "Help"
        page.save()
    page_errors = _logged_output_errors(caplog, error_type)
    return category_errors, page_errors


@pytest.mark.django_db
@pytest.mark.usefixtures("rag_store")
def test_an_output_error_at_the_commit_of_a_page_or_category_edit_is_logged_and_does_not_break_the_save(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    category, page = _category_and_page_with_dependents(
        django_capture_on_commit_callbacks
    )
    settings.MODEL_RAG_OUTPUT = {"BACKEND": "tests.rag_output.FailingOutput"}

    category_errors, page_errors = _errors_logged_by_editing_the_category_then_the_page(
        category, page, caplog, django_capture_on_commit_callbacks
    )

    assert category_errors
    assert page_errors
    assert Category.objects.get(pk=category.pk).name == "Cookware"
    assert Page.objects.get(pk=page.pk).title == "Help"


@pytest.mark.django_db
@pytest.mark.usefixtures("rag_store")
def test_an_output_that_cannot_be_built_at_the_commit_of_a_page_or_category_edit_is_logged_and_does_not_break_the_save(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    category, page = _category_and_page_with_dependents(
        django_capture_on_commit_callbacks
    )
    # set after the setup: the package checks it before each product's and
    # block's save
    settings.MODEL_RAG_OUTPUT = {"BACKEND": "tests.no_such_module.Output"}

    category_errors, page_errors = _errors_logged_by_editing_the_category_then_the_page(
        category, page, caplog, django_capture_on_commit_callbacks, ImproperlyConfigured
    )

    assert category_errors
    assert page_errors
    assert Category.objects.get(pk=category.pk).name == "Cookware"
    assert Page.objects.get(pk=page.pk).title == "Help"


@pytest.mark.django_db
@pytest.mark.usefixtures("rag_store")
def test_an_output_error_at_the_commit_of_a_page_or_category_edit_is_logged_with_the_failing_model_label(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    category, page = _category_and_page_with_dependents(
        django_capture_on_commit_callbacks
    )
    settings.MODEL_RAG_OUTPUT = {"BACKEND": "tests.rag_output.FailingOutput"}

    category_errors, page_errors = _errors_logged_by_editing_the_category_then_the_page(
        category, page, caplog, django_capture_on_commit_callbacks
    )

    category_messages = [record.getMessage() for record in category_errors]
    page_messages = [record.getMessage() for record in page_errors]
    assert any("catalog.product" in message for message in category_messages)
    assert any("pages.textplugin" in message for message in page_messages)
    assert any("pages.accordionitem" in message for message in page_messages)
