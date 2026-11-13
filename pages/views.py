from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from pages.models import Page


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html")


def page_detail(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(Page, slug=slug, language=get_language())
    return render(
        request,
        "pages/page_detail.html",
        {
            "page": page,
            "text_blocks": page.textplugin_set.order_by("pk"),
            "accordion_items": page.accordionitem_set.order_by("pk"),
        },
    )
