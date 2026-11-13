from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from catalog.models import Product


def product_list(request: HttpRequest) -> HttpResponse:
    products = (
        Product.objects.filter(language=get_language())
        .select_related("category")
        .order_by("category", "pk")
    )
    return render(request, "catalog/product_list.html", {"products": products})


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(
        Product.objects.select_related("category"), pk=pk, language=get_language()
    )
    return render(request, "catalog/product_detail.html", {"product": product})
