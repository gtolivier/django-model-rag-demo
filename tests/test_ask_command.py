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


def test_ask_prints_a_source_without_url_as_its_title_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_answer(question: str, **kwargs: object) -> Answer:
        return Answer(
            text="Fill it with vinegar, wait an hour, then rinse.",
            citations=(
                Citation(
                    title="Descaling notes",
                    url="",
                    source_key="pages.note:3",
                ),
            ),
        )

    monkeypatch.setattr("assistant.management.commands.ask.answer", fake_answer)
    stdout = StringIO()

    call_command("ask", "How do I descale a kettle?", stdout=stdout)

    assert stdout.getvalue().splitlines() == [
        "Fill it with vinegar, wait an hour, then rinse.",
        "Descaling notes",
    ]


def test_ask_says_so_when_nothing_indexed_is_close_enough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_answer(question: str, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("assistant.management.commands.ask.answer", fake_answer)
    stdout = StringIO()

    call_command("ask", "How do I descale a kettle?", stdout=stdout)

    assert stdout.getvalue().splitlines() == [
        "Nothing indexed is close enough to the question.",
    ]
