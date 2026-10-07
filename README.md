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
- `manage.py sync_model_rag` syncs everything; the project prints the
  documents through `ConsoleOutput`.

django-minimal-rag is installed but not wired yet.

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
uv sync
uv run python manage.py check
uv run python manage.py migrate
uv run python manage.py sync_model_rag
uv run pytest
```

The two packages are locked to specific commits in `uv.lock`. To move to
their latest `main`:

```sh
uv lock --upgrade-package django-model-rag --upgrade-package django-minimal-rag
```

## License

MIT — see [LICENSE](LICENSE).
