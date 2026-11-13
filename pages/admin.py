from django.contrib import admin

from pages.models import AccordionItem, Page, TextPlugin


class TextPluginInline(admin.StackedInline[TextPlugin, Page]):
    model = TextPlugin
    extra = 0


class AccordionItemInline(admin.StackedInline[AccordionItem, Page]):
    model = AccordionItem
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin[Page]):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}  # noqa: RUF012
    inlines = (TextPluginInline, AccordionItemInline)
