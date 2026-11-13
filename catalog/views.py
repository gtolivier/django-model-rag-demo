from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from catalog.models import Product


def _products_of_active_language() -> QuerySet[Product]:
    return Product.objects.filter(language=get_language()).select_related("category")


def product_list(request: HttpRequest) -> HttpResponse:
    products = _products_of_active_language().order_by("category", "pk")
    return render(request, "catalog/product_list.html", {"products": products})


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(_products_of_active_language(), pk=pk)
    return render(request, "catalog/product_detail.html", {"product": product})
