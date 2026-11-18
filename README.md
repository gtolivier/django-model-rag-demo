# django-model-rag-demo

Integration demo for
[django-model-rag](https://github.com/gtolivier/django-model-rag) and
[django-minimal-rag](https://github.com/gtolivier/django-minimal-rag).

**It is** a plain Django project that installs both packages **from their
Git repositories**, exactly as a third-party project would, and checks that
they work together. Its value as an integration test depends on that: it
never uses a local or editable install of either package.

**It is not** a reusable package, nor a production setup.

## Status

django-model-rag is wired: the demo's models sync to documents.

- `blog.Article` is the minimal example, below.
- `catalog.Product` is registered with declared fields; `pages` blocks
  (`TextPlugin`, `AccordionItem`) go through custom extractors. A block's
  document links to its page; an accordion item's, to the item itself
  (`/pages/faq/#accordion-3`), which the page opens when the URL names it,
  on load or when the fragment changes (this takes JavaScript: without it,
  the browser scrolls to the item, closed). Documents synced before the
  item links existed keep the page's URL until `sync_model_rag` runs again.
- Saving or deleting an instance updates its documents when the transaction
  commits. Editing a page or a category also updates the documents of its
  blocks or products, which declare what they read (`follow=["category"]`,
  `depends_on=["page"]`): the package does the rest, with no receiver of the
  project's own. A missing or invalid `MODEL_RAG_OUTPUT` raises
  `ImproperlyConfigured` at the save, before the row is written — that of a
  page or a category, created or edited, included.
- `manage.py sync_model_rag` syncs everything.
- `runserver` shows the shop: its home page, the cheeses by category, each
  page and the blog, as plain Django views and templates.
- The shop is in English at `/` and in French under `/fr/`
  (`i18n_patterns`), with a link to the other language on every page. Each
  article, product and page is written in one language, its `language`
  field: a view shows only those of the active language, and the documents
  carry it. django-model-rag guesses the field by its name; page blocks read
  their page's.

django-minimal-rag is wired behind it: `MODEL_RAG_OUTPUT` is its `Indexer`,
so the documents land in its chunk tables, in PostgreSQL with pgvector
(`compose.yaml` starts one on port 5434).

- Embeddings and answers come from [Ollama](https://ollama.com), through its
  OpenAI-compatible API: `bge-m3` for embeddings, `mistral-small3.2` for
  answers. The backends live in `assistant/backends.py`.
- Embedding is deferred (`MINIMAL_RAG_DEFER_EMBEDDING = True`): saving an
  instance stores its chunks without a vector, so a save never waits on
  Ollama, nor fails when it is down. `manage.py embed_pending` embeds them.
- `manage.py ask "question"` prints the answer, then its sources, one
  "title — URL" per line. It reads as an anonymous reader (no permissions),
  and says so when nothing indexed is close enough to the question: in
  French with `--language fr` (or `fr-CA`…), in English otherwise.
  `--max-distance` (default 0.5) and `--limit` (default 5) tune the
  retrieval. It searches every language unless `--language` names one, a
  BCP 47 language range: `fr` also covers `fr-CA`, but `en-CA` does not
  cover `en`. Documents of unknown language are kept either way.
- The shop's "Ask a question" page (`/chat/`, `/fr/chat/`) asks the same way
  `ask` does, with its default retrieval settings, in the language of the
  page: `/chat/` searches the English documents, `/fr/chat/` the French
  ones, both along with those of unknown language. It shows each answer
  with its sources and the extracts it comes from. The exchanges are kept
  for the visit (the session), oldest first, each page with its own: an
  exchange asked on `/fr/chat/` does not show on `/chat/`. With "Use the
  earlier exchanges" checked (the default), the question is asked with the
  page's last five exchanges as history, as shown — "nothing close enough"
  and "unavailable" included — so a follow-up question ("how long is it
  matured?") can lean on them; when the assistant searched with a rewritten
  question, the exchange shows it ("Searched for: …"). Unchecked, each
  question is answered on its own. The box is remembered for the visit,
  each page with its own. Once a page has exchanges, a "Clear the
  conversation" button removes them, and only them: the other page's
  exchanges and the rest of the session stay; the next question starts a
  new conversation. The page works without JavaScript; with it, an answer
  is added without reloading.

## Minimal example

The `blog` app shows the whole integration for a plain model. Two settings:

```python
# config/settings.py
INSTALLED_APPS = [
    # ...
    "django_model_rag",
    "blog",
]

MODEL_RAG_OUTPUT = {
    "BACKEND": "django_model_rag.output.ConsoleOutput",
}
```

(`ConsoleOutput` prints the documents; the demo itself sends them to
django-minimal-rag, as described in [Status](#status).)

and one registration, in the app's `model_rag.py`:

```python
# blog/model_rag.py
from django_model_rag import rag

from blog.models import Article

rag.register(Article)
```

The text fields are guessed: `title`, then `body`. The first one gives the
document title; `title_field=` names another field. The `language` field is
guessed too, and gives the document's language. From there, the documents
stay in sync as described in [Status](#status). `catalog` and `pages` show
what goes beyond that: declared fields, `follow`, custom extractors, and
keeping dependent documents up to date.

## Usage

```sh
docker compose up -d --wait
uv sync
uv run playwright install chromium
uv run python manage.py check
uv run python manage.py migrate
uv run pytest
```

To ask questions, install [Ollama](https://ollama.com), start it, and pull
the two models. `loaddata demo` fills the database with demo content: a
French cheese shop, with its cheeses, its pages (delivery, cheese boards,
questions) and a few blog posts, in English and in French. django-model-rag ignores the raw saves
`loaddata` makes, so `sync_model_rag` turns the content into documents
afterwards. Load it into an empty database:

```sh
ollama pull bge-m3
ollama pull mistral-small3.2
uv run python manage.py loaddata demo
uv run python manage.py sync_model_rag
uv run python manage.py embed_pending
uv run python manage.py ask "Which cheeses can I eat while pregnant?"
```

`uv run python manage.py runserver` then shows the shop at
http://127.0.0.1:8000/, and in French at http://127.0.0.1:8000/fr/; its
"Ask a question" page takes the same questions.

Other questions the content answers: "What wine goes with Comté?", "Do you
deliver to Belgium?", "How much cheese per guest for a wedding?", "Is the shop
open in mid-August?". They can be asked in French as well: "Quels fromages
puis-je manger enceinte ?", "Livrez-vous en Belgique ?". "What is the capital
of Peru?" finds nothing close enough.

The fixture sets primary keys: loading it again overwrites the objects that
hold them, and fails when another object already uses one of its slugs. Run
`sync_model_rag` and `embed_pending` after any load.

To edit the content, create an account, start the server and open
<http://localhost:8000/admin/>: articles, categories, products, and pages
with their blocks inline.

```sh
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Run `embed_pending` again after editing content: new chunks wait for it.
Three environment variables point the demo elsewhere:

| Variable | Default |
|---|---|
| `RAG_BASE_URL` | `http://localhost:11434/v1` |
| `RAG_EMBEDDING_MODEL` | `bge-m3` |
| `RAG_LLM_MODEL` | `mistral-small3.2` |

`RAG_BASE_URL` takes no trailing slash: the paths (`/embeddings`,
`/chat/completions`) are appended to it as is. After changing
`RAG_EMBEDDING_MODEL`, run `sync_model_rag` then `embed_pending` again: `ask`
only reads the chunks the current model embedded.

Known limits of `ask`, a demo command:

- Errors end in a traceback: Ollama not running, a model not pulled,
  `--limit 0`, a `--language` that is empty, holds whitespace or is `*`.
- Requests time out after 120 seconds, a setting no variable overrides; a
  slow first load of a model can exceed it.
- "Nothing indexed is close enough to the question." is printed without
  calling the model, so it follows `--language`, not the language of the
  question: a French question asked without `--language` gets it in
  English. It is also what an embedding model with no chunks yet gets, and
  a `--language` no document carries (`en-CA`: the demo's documents are
  `en` or `fr`): the cases look the same.
- When the model is called, it answers in the language of the question,
  most of the time: without `--language`, given extracts in both languages,
  it sometimes answers a French question in English.
- An empty answer from the model (`null` content) prints as `None`.
- Without `--language`, an English question and its French counterpart
  often both get the English and the French extract of the same content,
  which takes two of the `--limit` places.
- The model may still answer from what it knows rather than from the
  extracts, more often in French: "Vendez-vous du Gruyère ?" sometimes gets
  a "yes", which the content does not say.
- A question that asks for a whole list ("which cheeses do you sell?") gets
  at most `--limit` extracts, the nearest ones: similarity search does not
  enumerate a catalog. `--limit 30 --max-distance 0.6` brings the ten cheeses
  into the extracts, slowly, and the model may still leave one out of its
  answer.

The "Ask a question" page shares those limits, except that it shows "the
assistant is unavailable" instead of a traceback when Ollama cannot be
reached, and that it always uses the language of the page, where `ask`
needs `--language`: it searches only the documents in that language (and
those of unknown language), and says "nothing close enough" in it. Also:

- The page's language wins over the question's: a French question asked
  from `/chat/` gets English extracts.
- Posting an empty question, or one made only of spaces, shows the page with
  "Please type a question.", without the previous exchanges; they come back
  on the next visit of the page.
- When the server answers a question with an error, the script posts it
  again without JavaScript: the visitor waits twice for the same error.
- The session keeps every exchange of the visit, extracts included, and two
  questions posted at the same time from two tabs can lose one of them.
- A question waits for its whole answer, up to the 120-second timeout, with
  no progress shown beyond the button's "Looking for an answer…".

The two packages are locked to specific commits in `uv.lock`. To move to
their latest `main`:

```sh
uv lock --upgrade-package django-model-rag --upgrade-package django-minimal-rag
```

## License

MIT — see [LICENSE](LICENSE).
