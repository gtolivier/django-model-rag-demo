from decimal import Decimal

import pytest
from django.core.management import call_command
from pytest_django.fixtures import Settings

from catalog.models import Category, Product
from pages.models import Page, TextPlugin


@pytest.mark.django_db
def test_sync_with_the_project_settings_writes_each_source_key_and_title_on_stdout(
    settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    settings.MODEL_RAG_SIGNALS = False
    category = Category.objects.create(name="Kitchen")
    product = Product.objects.create(
        name="Kettle",
        description="Boils a litre of water in two minutes.",
        price=Decimal("29.90"),
        category=category,
    )
    page = Page.objects.create(title="About us", slug="about")
    text_block = TextPlugin.objects.create(page=page, body="We make kettles.")

    call_command("sync_model_rag")

    lines = capsys.readouterr().out.splitlines()
    assert f"catalog.product:{product.pk}" in lines
    assert "Kettle" in lines
    assert f"pages.textplugin:{text_block.pk}" in lines
    assert "About us" in lines
