from django_model_rag import NormalizedDocument, rag
from django_model_rag.extractors import BaseExtractor

from pages.models import AccordionItem, TextPlugin


@rag.register_extractor(AccordionItem)
class AccordionItemExtractor(BaseExtractor[AccordionItem]):
    def extract(self, instance: AccordionItem) -> NormalizedDocument:
        return self.build_document(
            instance,
            text=f"{instance.title}\n\n{instance.body}",
            title=f"{instance.page.title} — {instance.title}",
            url=instance.page.get_absolute_url(),
        )


@rag.register_extractor(TextPlugin)
class TextPluginExtractor(BaseExtractor[TextPlugin]):
    def extract(self, instance: TextPlugin) -> NormalizedDocument:
        return self.build_document(
            instance,
            text=instance.body,
            title=instance.page.title,
            url=instance.page.get_absolute_url(),
        )
