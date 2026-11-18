from collections.abc import Iterable

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import add_never_cache_headers
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_minimal_rag.answering import Answer, Citation, Exchange, answer
from django_minimal_rag.retrieval import RetrievedChunk

from assistant.answering import MAX_CHUNKS, MAX_DISTANCE, NOTHING_CLOSE_ENOUGH
from pages.models import pages_in_active_language

EXCHANGES_SESSION_KEY_PREFIX = "exchanges"
USE_HISTORY_SESSION_KEY_PREFIX = "use_history"
MAX_HISTORY_EXCHANGES = 5
QUESTION_REQUIRED = _("Please type a question.")
ASSISTANT_UNAVAILABLE = _("The assistant is unavailable right now. Try again later.")


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html")


def chat(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _post_question(request)
    response = render(
        request,
        "pages/chat.html",
        {
            "exchanges": _exchanges(request),
            "use_history": request.session.get(_use_history_session_key(), True),
        },
    )
    add_never_cache_headers(response)
    return response


@require_POST
def chat_reset(request: HttpRequest) -> HttpResponse:
    request.session.pop(_exchanges_session_key(), None)
    return redirect("chat")


def _post_question(request: HttpRequest) -> HttpResponse:
    question = request.POST.get("question", "")
    if not question.strip():
        return render(
            request,
            "pages/chat.html",
            {"error": QUESTION_REQUIRED},
            status=400,
        )
    request.session[_use_history_session_key()] = _is_history_requested(request)
    exchange = _ask(question, _history(request))
    request.session[_exchanges_session_key()] = [*_exchanges(request), exchange]
    if _is_fetch_request(request):
        return render(request, "pages/chat_exchange.html", {"exchange": exchange})
    return redirect(request.path)


def _history(request: HttpRequest) -> tuple[Exchange, ...] | None:
    if not _is_history_requested(request):
        return None
    return tuple(
        Exchange(question=str(earlier["question"]), answer=str(earlier["text"]))
        for earlier in _exchanges(request)[-MAX_HISTORY_EXCHANGES:]
    )


def _is_history_requested(request: HttpRequest) -> bool:
    return request.POST.get("use_history") == "on"


def _use_history_session_key() -> str:
    return _active_language_session_key(USE_HISTORY_SESSION_KEY_PREFIX)


def _exchanges_session_key() -> str:
    return _active_language_session_key(EXCHANGES_SESSION_KEY_PREFIX)


def _active_language_session_key(prefix: str) -> str:
    return f"{prefix}_{get_language()}"


def _exchanges(request: HttpRequest) -> list[dict[str, object]]:
    exchanges: list[dict[str, object]] = request.session.get(
        _exchanges_session_key(), []
    )
    return exchanges


def _ask(question: str, history: tuple[Exchange, ...] | None) -> dict[str, object]:
    history_kwargs = {} if history is None else {"history": history}
    try:
        reply = answer(
            question,
            language=get_language(),
            permissions=frozenset(),
            max_distance=MAX_DISTANCE,
            limit=MAX_CHUNKS,
            **history_kwargs,
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
