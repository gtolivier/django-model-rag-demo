from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django_minimal_rag.answering import Citation, answer

MAX_DISTANCE = 0.5
MAX_CHUNKS = 5


class Command(BaseCommand):
    help = "Answer a question from the indexed content."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("question")

    def handle(self, *args: Any, **options: Any) -> None:
        result = answer(
            options["question"],
            permissions=frozenset(),
            max_distance=MAX_DISTANCE,
            limit=MAX_CHUNKS,
        )
        if result is None:
            self.stdout.write("Nothing indexed is close enough to the question.")
            return
        self.stdout.write(result.text)
        for citation in result.citations:
            self.stdout.write(source_line(citation))


def source_line(citation: Citation) -> str:
    if not citation.url:
        return citation.title
    return f"{citation.title} — {citation.url}"
