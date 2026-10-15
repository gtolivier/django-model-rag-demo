from io import StringIO

import pytest
from django.core.management import call_command
from django_minimal_rag.answering import Answer, Citation


def test_ask_prints_the_answer_then_one_line_per_source_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_answer(question: str, **kwargs: object) -> Answer:
        return Answer(
            text="Fill it with vinegar, wait an hour, then rinse.",
            citations=(
                Citation(
                    title="Descaling a kettle",
                    url="/blog/descaling-a-kettle/",
                    source_key="blog.article:1",
                ),
                Citation(
                    title="Kettle care",
                    url="/pages/kettle-care/",
                    source_key="pages.page:7",
                ),
            ),
        )

    monkeypatch.setattr("assistant.management.commands.ask.answer", fake_answer)
    stdout = StringIO()

    call_command("ask", "How do I descale a kettle?", stdout=stdout)

    assert stdout.getvalue().splitlines() == [
        "Fill it with vinegar, wait an hour, then rinse.",
        "Descaling a kettle — /blog/descaling-a-kettle/",
        "Kettle care — /pages/kettle-care/",
    ]
