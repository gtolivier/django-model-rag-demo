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

- `catalog.Product` is registered with declared fields; `pages` blocks
  (`TextPlugin`, `AccordionItem`) go through custom extractors.
- Saving or deleting an instance updates its documents when the transaction
  commits. Editing a page or a category also updates the documents of its
  blocks or products.
- `manage.py sync_model_rag` syncs everything; the project prints the
  documents through `ConsoleOutput`.

django-minimal-rag is installed but not wired yet.

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
