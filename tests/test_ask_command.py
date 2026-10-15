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


def test_ask_asks_as_an_anonymous_reader_within_distance_and_limit_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_answer(question: str, **kwargs: object) -> None:
        calls.append((question, kwargs))

    monkeypatch.setattr("assistant.management.commands.ask.answer", fake_answer)

    call_command("ask", "How do I descale a kettle?", stdout=StringIO())

    assert calls == [
        (
            "How do I descale a kettle?",
            {"permissions": frozenset(), "max_distance": 0.5, "limit": 5},
        )
    ]


def test_ask_passes_the_max_distance_and_limit_options_to_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_answer(question: str, **kwargs: object) -> None:
        calls.append((question, kwargs))

    monkeypatch.setattr("assistant.management.commands.ask.answer", fake_answer)

    call_command(
        "ask",
        "How do I descale a kettle?",
        "--max-distance",
        "0.8",
        "--limit",
        "3",
        stdout=StringIO(),
    )

    assert len(calls) == 1
    question, kwargs = calls[0]
    assert question == "How do I descale a kettle?"
    assert kwargs["max_distance"] == 0.8
    assert type(kwargs["max_distance"]) is float
    assert kwargs["limit"] == 3
    assert type(kwargs["limit"]) is int
