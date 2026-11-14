from django.http import HttpRequest

from pages.models import pages_in_active_language


def nav_pages(request: HttpRequest) -> dict[str, object]:
    return {"nav_pages": pages_in_active_language().order_by("pk")}
