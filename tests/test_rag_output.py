from collections.abc import Sequence

from django_model_rag import NormalizedDocument

from config.rag_output import DictOutput


def _document(text: str) -> NormalizedDocument:
    return NormalizedDocument(
        text=text,
        source_app_label="catalog",
        source_model="book",
        source_pk=1,
    )


def test_replace_stores_each_group_in_place_of_what_its_key_held() -> None:
    old = _document("old text")
    new = _document("new text")
    store: dict[str, Sequence[NormalizedDocument]] = {new.source_key: [old]}
    output = DictOutput(store=store)

    output.replace({new.source_key: [new]})

    assert list(store[new.source_key]) == [new]


def test_replace_removes_the_key_of_an_empty_group_and_ignores_unknown_keys() -> None:
    held = _document("held text")
    absent_key = "a key the store does not hold"
    store: dict[str, Sequence[NormalizedDocument]] = {held.source_key: [held]}
    output = DictOutput(store=store)

    output.replace({held.source_key: [], absent_key: []})

    assert store == {}


def test_prune_removes_the_unkept_keys_of_the_model_only() -> None:
    kept = [_document("kept text")]
    unkept = [_document("unkept text")]
    other_model = [_document("other model text")]
    store: dict[str, Sequence[NormalizedDocument]] = {
        "catalog.product:1": kept,
        "catalog.product:2": unkept,
        "catalog.book:2": other_model,
    }
    output = DictOutput(store=store)

    output.prune("catalog.product", {"catalog.product:1"})

    assert store == {"catalog.product:1": kept, "catalog.book:2": other_model}
