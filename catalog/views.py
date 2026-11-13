from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from catalog.models import Product


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=pk)
    return render(request, "catalog/product_detail.html", {"product": product})
