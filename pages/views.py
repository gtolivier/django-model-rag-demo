from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_minimal_rag.answering import answer

from assistant.management.commands.ask import MAX_CHUNKS, MAX_DISTANCE
from pages.models import pages_in_active_language

EXCHANGE_SESSION_KEY = "exchange"


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
        request.session[EXCHANGE_SESSION_KEY] = {
            "question": question,
            "text": reply.text if reply else "",
        }
        return redirect(request.path)
    return render(
        request,
        "pages/chat.html",
        {"exchange": request.session.pop(EXCHANGE_SESSION_KEY, None)},
    )


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
