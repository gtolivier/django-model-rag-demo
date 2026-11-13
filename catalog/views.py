from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from catalog.models import Product


def product_list(request: HttpRequest) -> HttpResponse:
    products = Product.objects.select_related("category").order_by("category", "pk")
    return render(request, "catalog/product_list.html", {"products": products})


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    return render(request, "catalog/product_detail.html", {"product": product})
