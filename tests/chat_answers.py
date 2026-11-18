import pytest
from django_minimal_rag.answering import Answer

CHAT_ANSWER = "pages.views.answer"


def answer_every_question_with(monkeypatch: pytest.MonkeyPatch, answer: Answer) -> None:
    """Replace the chat page's answer() with a fake that always returns answer."""
    monkeypatch.setattr(CHAT_ANSWER, lambda question, **kwargs: answer)


def answer_each_question_from(
    monkeypatch: pytest.MonkeyPatch, replies: dict[str, str]
) -> list[str]:
    """Replace the chat page's answer() with a fake that answers from replies.

    The fake finds nothing, and returns a list of the questions it was asked.
    """
    questions: list[str] = []

    def fake_answer(question: str, **kwargs: object) -> Answer:
        questions.append(question)
        return Answer(
            text=replies.get(question, "An unexpected question."),
            chunks=(),
            search_question=question,
        )

    monkeypatch.setattr(CHAT_ANSWER, fake_answer)
    return questions
