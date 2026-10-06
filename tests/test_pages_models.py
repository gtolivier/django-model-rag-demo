import pytest
from django.db import IntegrityError

from pages.models import Page


@pytest.mark.django_db
def test_two_pages_cannot_share_a_slug() -> None:
    Page.objects.create(title="About us", slug="about")

    with pytest.raises(IntegrityError):
        Page.objects.create(title="About the team", slug="about")
