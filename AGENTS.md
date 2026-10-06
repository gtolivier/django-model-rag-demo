# AGENTS.md

Instructions for coding agents working in this repository. Read
[README.md](README.md) first.

## Commands

- Install: `uv sync`
- Test: `uv run pytest`
- Check: `uv run python manage.py check`
- Lint: `uv run ruff check` — format: `uv run ruff format`
- Type check: `uv run --group typecheck mypy` (strict, with the django-stubs plugin)

Always go through `uv run`; do not rely on an activated virtualenv.

## Layout

- `config/` — the Django project (settings, URLs).
- `blog/` — the minimal example: one model, registered with
  `rag.register()` alone.
- `catalog/`, `pages/` — the demo apps that show the advanced cases.
- `tests/` — pytest tests (`test_*.py`), run with pytest-django against
  `config.settings`.

## Test-driven development

Features are built with the `/tdd:feature` skill of the
[`tdd` plugin](https://github.com/gtolivier/agent-workflows). Its conventions
for this repository:

- **Test, lint, type-check and format commands:** those of the Commands
  section above.
- **Test files:** everything under `tests/`. Nothing outside `tests/` is a
  test file.
- **Production code:** `blog/`, `catalog/`, `pages/` and `config/`.
- **Migrations:** generated, never written by hand. After changing a model,
  run `uv run python manage.py makemigrations`, then
  `uv run ruff format` (Django's output does not pass ruff).
- **Package sources:** to read the code of django-model-rag or
  django-minimal-rag, look only at the installed copy under `.venv/`, never
  at a checkout elsewhere on disk: the demo tests what `uv.lock` installs.
- **Don't test the packages.** The demo's tests cover what the demo brings:
  its models, extractors, registration, settings, URLs and wiring (signals in
  a real project, cascades, query counts of its own extractors). A behavior
  django-model-rag or django-minimal-rag already guarantees belongs to their
  own suites, not here. Those tests are not in the installed wheel: read them
  on GitHub, at the commit locked in `uv.lock`. A red test that is already
  green is a strong hint the behavior is the package's.

## Rules

- **Install the packages from Git only.** `django-model-rag` and
  `django-minimal-rag` come from their GitHub repositories, locked to a
  commit in `uv.lock`. Never replace them with a local path or an editable
  install (`uv add --editable ../…`): this repository exists to test them as
  a third party would, and a local link silently defeats that.
- **Moving to newer commits** is a deliberate step:
  `uv lock --upgrade-package <name>`, then commit the updated `uv.lock`.
- **Dependencies:** add or remove them with `uv add` / `uv remove`, never by
  editing `pyproject.toml` by hand.
- **Generated files:** use `manage.py startapp`, `manage.py makemigrations`
  and other official generators instead of writing those files by hand.
- **No secrets:** this repository is public. `SECRET_KEY` is read from the
  `DJANGO_SECRET_KEY` environment variable; the fallback in
  `config/settings.py` is public and for local use only.
- **No `CLAUDE.md`:** this file is the single source of agent instructions.
  A `CLAUDE.md` next to it would make Claude Code ignore it.
