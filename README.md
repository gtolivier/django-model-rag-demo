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
  (`TextPlugin`, `AccordionItem`) go through custom extractors.
- Saving or deleting an instance updates its documents when the transaction
  commits. Editing a page or a category also updates the documents of its
  blocks or products, which declare what they read (`follow=["category"]`,
  `depends_on=["page"]`): the package does the rest, with no receiver of the
  project's own. A missing or invalid `MODEL_RAG_OUTPUT` raises
  `ImproperlyConfigured` at the save, before the row is written — that of a
  page or a category, created or edited, included.
- `manage.py sync_model_rag` syncs everything.

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
  and says so when nothing indexed is close enough to the question.
  `--max-distance` (default 0.5) and `--limit` (default 5) tune the
  retrieval.

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
document title; `title_field=` names another field. From there, the documents
stay in sync as described in [Status](#status). `catalog` and `pages` show
what goes beyond that: declared fields, `follow`, custom extractors, and
keeping dependent documents up to date.

## Usage

```sh
docker compose up -d --wait
uv sync
uv run python manage.py check
uv run python manage.py migrate
uv run pytest
```

To ask questions, install [Ollama](https://ollama.com), start it, and pull
the two models:

```sh
ollama pull bge-m3
ollama pull mistral-small3.2
uv run python manage.py sync_model_rag
uv run python manage.py embed_pending
uv run python manage.py ask "What is on sale?"
```

Run `embed_pending` again after editing content: new chunks wait for it.
Three environment variables point the demo elsewhere:

| Variable | Default |
|---|---|
| `RAG_BASE_URL` | `http://localhost:11434/v1` |
| `RAG_EMBEDDING_MODEL` | `bge-m3` |
| `RAG_LLM_MODEL` | `mistral-small3.2` |

After changing `RAG_EMBEDDING_MODEL`, run `sync_model_rag` then
`embed_pending` again: `ask` only reads the chunks the current model
embedded.

The two packages are locked to specific commits in `uv.lock`. To move to
their latest `main`:

```sh
uv lock --upgrade-package django-model-rag --upgrade-package django-minimal-rag
```

## License

MIT — see [LICENSE](LICENSE).
