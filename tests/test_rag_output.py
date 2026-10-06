from django_model_rag import DocumentOutput, NormalizedDocument

from config.rag_output import DictOutput
from tests.conftest import DocumentStore


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
    store: DocumentStore = {new.source_key: [old]}
    output = DictOutput(store=store)

    output.replace({new.source_key: [new]})

    assert list(store[new.source_key]) == [new]


def test_replace_removes_the_key_of_an_empty_group_and_ignores_unknown_keys() -> None:
    held = _document("held text")
    absent_key = "a key the store does not hold"
    store: DocumentStore = {held.source_key: [held]}
    output = DictOutput(store=store)

    output.replace({held.source_key: [], absent_key: []})

    assert store == {}


def test_prune_removes_the_unkept_keys_of_the_model_only() -> None:
    kept = [_document("kept text")]
    unkept = [_document("unkept text")]
    other_model = [_document("other model text")]
    store: DocumentStore = {
        "catalog.product:1": kept,
        "catalog.product:2": unkept,
        "catalog.book:2": other_model,
    }
    output = DictOutput(store=store)

    output.prune("catalog.product", {"catalog.product:1"})

    assert store == {"catalog.product:1": kept, "catalog.book:2": other_model}


def test_dict_output_is_a_document_output_of_the_package() -> None:
    document = _document("text")
    store: DocumentStore = {}
    output: DocumentOutput = DictOutput(store=store)

    output.replace({document.source_key: [document]})

    assert list(store[document.source_key]) == [document]
