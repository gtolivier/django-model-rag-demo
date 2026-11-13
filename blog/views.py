from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from blog.models import Article


def _articles_in_active_language() -> QuerySet[Article]:
    return Article.objects.filter(language=get_language())


def article_list(request: HttpRequest) -> HttpResponse:
    articles = _articles_in_active_language().order_by("-pk")
    return render(request, "blog/article_list.html", {"articles": articles})


def article_detail(request: HttpRequest, pk: int) -> HttpResponse:
    article = get_object_or_404(_articles_in_active_language(), pk=pk)
    return render(request, "blog/article_detail.html", {"article": article})
