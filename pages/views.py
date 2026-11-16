from collections.abc import Iterable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_minimal_rag.answering import Answer, Citation, answer
from django_minimal_rag.retrieval import RetrievedChunk

from assistant.management.commands.ask import (
    MAX_CHUNKS,
    MAX_DISTANCE,
    NOTHING_CLOSE_ENOUGH,
)
from pages.models import pages_in_active_language

EXCHANGES_SESSION_KEY = "exchanges"


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html")


def chat(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        question = request.POST.get("question", "")
        if not question:
            return render(request, "pages/chat.html", status=400)
        reply = answer(
            question,
            permissions=frozenset(),
            max_distance=MAX_DISTANCE,
            limit=MAX_CHUNKS,
        )
        if _is_fetch_request(request):
            return render(request, "pages/chat_exchange.html", {"question": question})
        request.session[EXCHANGES_SESSION_KEY] = [
            *request.session.get(EXCHANGES_SESSION_KEY, []),
            _exchange(question, reply),
        ]
        return redirect(request.path)
    return render(
        request,
        "pages/chat.html",
        {"exchanges": request.session.get(EXCHANGES_SESSION_KEY, [])},
    )


def _exchange(question: str, reply: Answer | None) -> dict[str, object]:
    return {
        "question": question,
        "text": reply.text if reply else str(NOTHING_CLOSE_ENOUGH),
        "sources": _sources(reply.citations) if reply else [],
        "extracts": _extracts(reply.chunks) if reply else [],
    }


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
