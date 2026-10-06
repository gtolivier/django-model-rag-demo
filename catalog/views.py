from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from catalog.models import Product


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=pk)
    return HttpResponse(f"{product.name}\n\n{product.description}")
