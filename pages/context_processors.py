from django.http import HttpRequest

from pages.models import Page


def nav_pages(request: HttpRequest) -> dict[str, object]:
    return {"nav_pages": Page.objects.order_by("pk")}
