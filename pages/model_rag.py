from django.db.models import QuerySet
from django_model_rag import NormalizedDocument, rag
from django_model_rag.extractors import BaseExtractor

from pages.models import AccordionItem, TextPlugin


class PageBlockExtractor[M: AccordionItem | TextPlugin](BaseExtractor[M]):
    # each block's document reads its page: load it in the same query
    def get_queryset(self, queryset: QuerySet[M]) -> QuerySet[M]:
        return queryset.select_related("page")

    def build_block_document(
        self, instance: M, *, text: str, title: str
    ) -> NormalizedDocument:
        # a block has no view of its own: its document links to its page
        return self.build_document(
            instance, text=text, title=title, url=instance.page.get_absolute_url()
        )


@rag.register_extractor(AccordionItem, depends_on=["page"])
class AccordionItemExtractor(PageBlockExtractor[AccordionItem]):
    def extract(self, instance: AccordionItem) -> NormalizedDocument | None:
        text = f"{instance.title}\n\n{instance.body}".strip()
        if not text:
            return None
        title = instance.page.title
        if instance.title:
            title = f"{title} — {instance.title}"
        return self.build_block_document(instance, text=text, title=title)


@rag.register_extractor(TextPlugin, depends_on=["page"])
class TextPluginExtractor(PageBlockExtractor[TextPlugin]):
    def extract(self, instance: TextPlugin) -> NormalizedDocument | None:
        text = instance.body.strip()
        if not text:
            return None
        return self.build_block_document(instance, text=text, title=instance.page.title)
