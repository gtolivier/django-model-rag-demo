from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from pages.models import Page


def page_detail(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(Page, slug=slug)
    lines = [page.title]
    for plugin in page.textplugin_set.all():
        lines.append(plugin.body)
    for item in page.accordionitem_set.all():
        lines.append(item.title)
        lines.append(item.body)
    return HttpResponse("\n".join(lines), content_type="text/plain")
