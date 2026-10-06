from django.db.models import QuerySet
from django_model_rag import NormalizedDocument, rag
from django_model_rag.extractors import BaseExtractor

from pages.models import AccordionItem, TextPlugin


class PageBlockExtractor[M: AccordionItem | TextPlugin](BaseExtractor[M]):
    # each block's document reads its page: load it in the same query
    def get_queryset(self, queryset: QuerySet[M]) -> QuerySet[M]:
        return queryset.select_related("page")


@rag.register_extractor(AccordionItem)
class AccordionItemExtractor(PageBlockExtractor[AccordionItem]):
    def extract(self, instance: AccordionItem) -> NormalizedDocument | None:
        text = f"{instance.title}\n\n{instance.body}".strip()
        if not text:
            return None
        return self.build_document(
            instance,
            text=text,
            title=f"{instance.page.title} — {instance.title}",
            url=instance.page.get_absolute_url(),
        )


@rag.register_extractor(TextPlugin)
class TextPluginExtractor(PageBlockExtractor[TextPlugin]):
    def extract(self, instance: TextPlugin) -> NormalizedDocument | None:
        if not instance.body.strip():
            return None
        return self.build_document(
            instance,
            text=instance.body.strip(),
            title=instance.page.title,
            url=instance.page.get_absolute_url(),
        )
