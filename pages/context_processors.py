from django.http import HttpRequest
from django.utils.translation import get_language

from pages.models import Page


def nav_pages(request: HttpRequest) -> dict[str, object]:
    return {"nav_pages": Page.objects.filter(language=get_language()).order_by("pk")}
