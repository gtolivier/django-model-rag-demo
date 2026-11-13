from django.contrib import admin

from catalog.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin[Category]):
    list_display = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin[Product]):
    list_display = ("name", "category", "price")
    list_filter = ("category",)
    search_fields = ("name", "description")
