from typing import Any

from django.db.models import QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_model_rag import NormalizedDocument, rag
from django_model_rag.extractors import BaseExtractor

from config.rag_sync import sync_on_commit
from pages.models import AccordionItem, Page, TextPlugin


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


@rag.register_extractor(AccordionItem)
class AccordionItemExtractor(PageBlockExtractor[AccordionItem]):
    def extract(self, instance: AccordionItem) -> NormalizedDocument | None:
        text = f"{instance.title}\n\n{instance.body}".strip()
        if not text:
            return None
        return self.build_block_document(
            instance, text=text, title=f"{instance.page.title} — {instance.title}"
        )


@rag.register_extractor(TextPlugin)
class TextPluginExtractor(PageBlockExtractor[TextPlugin]):
    def extract(self, instance: TextPlugin) -> NormalizedDocument | None:
        text = instance.body.strip()
        if not text:
            return None
        return self.build_block_document(instance, text=text, title=instance.page.title)


@receiver(post_save, sender=Page)
def sync_blocks_of_saved_page(
    sender: type[Page],
    instance: Page,
    created: bool = False,
    raw: bool = False,
    **kwargs: Any,
) -> None:
    # the blocks' documents carry the page's title and url. A new page has no
    # blocks yet: each one added later syncs on its own save.
    if raw or created:
        return

    sync_on_commit(
        AccordionItem.objects.filter(page=instance.pk),
        TextPlugin.objects.filter(page=instance.pk),
    )
