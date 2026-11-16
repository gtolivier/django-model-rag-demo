from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django_minimal_rag.answering import Citation, answer

from assistant.answering import MAX_CHUNKS, MAX_DISTANCE, NOTHING_CLOSE_ENOUGH

__all__ = [
    "MAX_CHUNKS",
    "MAX_DISTANCE",
    "NOTHING_CLOSE_ENOUGH",
    "Command",
    "source_line",
]


class Command(BaseCommand):
    help = "Answer a question from the indexed content."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("question")
        parser.add_argument("--max-distance", type=float, default=MAX_DISTANCE)
        parser.add_argument("--limit", type=int, default=MAX_CHUNKS)

    def handle(self, *args: Any, **options: Any) -> None:
        result = answer(
            options["question"],
            permissions=frozenset(),
            max_distance=options["max_distance"],
            limit=options["limit"],
        )
        if result is None:
            self.stdout.write(str(NOTHING_CLOSE_ENOUGH))
            return
        self.stdout.write(result.text)
        for citation in result.citations:
            self.stdout.write(source_line(citation))


def source_line(citation: Citation) -> str:
    if not citation.url:
        return citation.title
    return f"{citation.title} — {citation.url}"
