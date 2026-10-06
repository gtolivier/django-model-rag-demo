from collections.abc import Collection, Mapping, Sequence

from django_model_rag import NormalizedDocument

# Source keys read "app_label.model:pk"; the package does not export its builder.
SOURCE_KEY_SEPARATOR = ":"


class DictOutput:
    """Keeps the documents in a dict, under their source key."""

    def __init__(self, store: dict[str, Sequence[NormalizedDocument]]) -> None:
        self._store = store

    def replace(self, groups: Mapping[str, Sequence[NormalizedDocument]]) -> None:
        for key, documents in groups.items():
            if documents:
                self._store[key] = documents
            else:
                self._store.pop(key, None)

    def prune(self, model_label: str, kept_keys: Collection[str]) -> None:
        prefix = f"{model_label}{SOURCE_KEY_SEPARATOR}"
        for key in list(self._store):
            if key.startswith(prefix) and key not in kept_keys:
                del self._store[key]
