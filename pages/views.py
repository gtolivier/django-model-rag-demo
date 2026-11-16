from collections.abc import Iterable

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django_minimal_rag.answering import Answer, Citation, answer
from django_minimal_rag.retrieval import RetrievedChunk

from assistant.answering import MAX_CHUNKS, MAX_DISTANCE, NOTHING_CLOSE_ENOUGH
from pages.models import pages_in_active_language

EXCHANGES_SESSION_KEY = "exchanges"
QUESTION_REQUIRED = _("Please type a question.")
ASSISTANT_UNAVAILABLE = _("The assistant is unavailable right now. Try again later.")


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html")


def chat(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _post_question(request)
    return render(request, "pages/chat.html", {"exchanges": _exchanges(request)})


def _post_question(request: HttpRequest) -> HttpResponse:
    question = request.POST.get("question", "")
    if not question.strip():
        return render(
            request,
            "pages/chat.html",
            {"error": QUESTION_REQUIRED},
            status=400,
        )
    exchange = _ask(question)
    request.session[EXCHANGES_SESSION_KEY] = [*_exchanges(request), exchange]
    if _is_fetch_request(request):
        return render(request, "pages/chat_exchange.html", {"exchange": exchange})
    return redirect(request.path)


def _exchanges(request: HttpRequest) -> list[dict[str, object]]:
    exchanges: list[dict[str, object]] = request.session.get(EXCHANGES_SESSION_KEY, [])
    return exchanges


def _ask(question: str) -> dict[str, object]:
    try:
        reply = answer(
            question,
            language="en",
            permissions=frozenset(),
            max_distance=MAX_DISTANCE,
            limit=MAX_CHUNKS,
        )
    except httpx.HTTPError:
        return _message_exchange(question, str(ASSISTANT_UNAVAILABLE))
    if reply is None:
        return _message_exchange(question, str(NOTHING_CLOSE_ENOUGH))
    return _exchange(question, reply)


def _exchange(question: str, reply: Answer) -> dict[str, object]:
    return {
        "question": question,
        "text": reply.text,
        "sources": _sources(reply.citations),
        "extracts": _extracts(reply.chunks),
    }


def _message_exchange(question: str, message: str) -> dict[str, object]:
    return {"question": question, "text": message, "sources": [], "extracts": []}


def _sources(citations: Iterable[Citation]) -> list[dict[str, str]]:
    return [{"title": citation.title, "url": citation.url} for citation in citations]


def _extracts(chunks: Iterable[RetrievedChunk]) -> list[dict[str, str]]:
    return [{"title": chunk.title, "text": chunk.text} for chunk in chunks]


def _is_fetch_request(request: HttpRequest) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def page_detail(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(pages_in_active_language(), slug=slug)
    return render(
        request,
        "pages/page_detail.html",
        {
            "page": page,
            "text_blocks": page.textplugin_set.order_by("pk"),
            "accordion_items": page.accordionitem_set.order_by("pk"),
        },
    )
