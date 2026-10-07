from collections.abc import Collection, Mapping, Sequence

from django_model_rag import NormalizedDocument
from django_model_rag.documents import build_source_key

DocumentStore = dict[str, Sequence[NormalizedDocument]]


class DictOutput:
    """Keeps the documents in a dict, under their source key."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def replace(self, groups: Mapping[str, Sequence[NormalizedDocument]]) -> None:
        for key, documents in groups.items():
            if documents:
                self._store[key] = documents
            else:
                self._store.pop(key, None)

    def prune(self, model_label: str, kept_keys: Collection[str]) -> None:
        # A key with an empty pk is the prefix every key of the model shares.
        prefix = build_source_key(model_label, "")
        for key in list(self._store):
            if key.startswith(prefix) and key not in kept_keys:
                del self._store[key]
