# AGENTS.md

Instructions for coding agents working in this repository. Read
[README.md](README.md) first.

## Commands

- Install: `uv sync`
- Check: `uv run python manage.py check`
- Lint: `uv run ruff check` — format: `uv run ruff format`

Always go through `uv run`; do not rely on an activated virtualenv.

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
