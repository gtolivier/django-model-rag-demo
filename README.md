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

Skeleton: the project loads both packages as Django apps
(`manage.py check`). Nothing else is wired yet.

## Usage

```sh
uv sync
uv run python manage.py check
```

The two packages are locked to specific commits in `uv.lock`. To move to
their latest `main`:

```sh
uv lock --upgrade-package django-model-rag --upgrade-package django-minimal-rag
```

## License

MIT — see [LICENSE](LICENSE).
