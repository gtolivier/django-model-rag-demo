from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_model_rag import NormalizedDocument, SyncPipeline, rag
from django_model_rag.extractors import BaseExtractor
from django_model_rag.output import configured_output

from pages.models import AccordionItem, Page, TextPlugin


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
        text = instance.body.strip()
        if not text:
            return None
        return self.build_document(
            instance,
            text=text,
            title=instance.page.title,
            url=instance.page.get_absolute_url(),
        )


@receiver(post_save, sender=Page)
def sync_blocks_of_saved_page(
    sender: type[Page], instance: Page, raw: bool = False, **kwargs: Any
) -> None:
    # the blocks' documents carry the page's title and url
    if raw:
        return

    def sync_blocks() -> None:
        pipeline = SyncPipeline(configured_output())
        for model in (AccordionItem, TextPlugin):
            for block in model.objects.filter(page=instance.pk):
                pipeline.run_instance(block)

    transaction.on_commit(sync_blocks)
