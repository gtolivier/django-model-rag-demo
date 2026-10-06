from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from pages.models import Page


def page_detail(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(Page, slug=slug)
    return HttpResponse(page.title)
