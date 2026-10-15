from typing import Any

from django.core.management.base import BaseCommand
from django_minimal_rag.indexing import embed_pending


class Command(BaseCommand):
    help = "Embed the chunks that are waiting for an embedding."

    def handle(self, *args: Any, **options: Any) -> None:
        embedded = embed_pending()
        self.stdout.write(f"Embedded {embedded} chunks.")
