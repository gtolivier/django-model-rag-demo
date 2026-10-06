from io import StringIO

import pytest
from django.core.management import call_command

from tests.conftest import DocumentStore


@pytest.mark.django_db
def test_sync_announces_each_registered_model_in_the_order_of_the_installed_apps(
    rag_store: DocumentStore,
) -> None:
    stdout = StringIO()

    call_command("sync_model_rag", stdout=stdout)

    assert stdout.getvalue().splitlines() == [
        "catalog.product: synced",
        "pages.accordionitem: synced",
        "pages.textplugin: synced",
    ]
