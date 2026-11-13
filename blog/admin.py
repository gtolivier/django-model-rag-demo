from django.contrib import admin

from blog.models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin[Article]):
    list_display = ("title",)
    search_fields = ("title", "body")
