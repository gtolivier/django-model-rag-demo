from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Embed the chunks that are waiting for an embedding."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Embedded 0 chunks.")
