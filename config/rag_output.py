from collections.abc import Mapping, Sequence

from django_model_rag import NormalizedDocument


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
