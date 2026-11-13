from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from pages.models import Page


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html", {"pages": Page.objects.all()})


def page_detail(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(Page, slug=slug)
    return render(request, "pages/page_detail.html", {"page": page})
