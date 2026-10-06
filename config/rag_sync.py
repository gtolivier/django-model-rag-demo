import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Model, QuerySet
from django_model_rag import SyncPipeline, rag
from django_model_rag.documents import model_source_key
from django_model_rag.output import configured_output

_SIGNALS_SETTING = "MODEL_RAG_SIGNALS"

logger = logging.getLogger("django_model_rag")


def _signals_enabled() -> bool:
    """Return whether the package's signals sync anything, as the settings say."""
    return bool(getattr(settings, _SIGNALS_SETTING, True))


def sync_on_commit(*querysets: QuerySet[Any]) -> None:
    """Hand the documents of the instances of ``querysets`` to the output at commit.

    For instances whose documents carry the fields of another model: the
    package syncs an instance on its own save, not on the save of what it reads.
    """
    if not _signals_enabled():
        return

    def sync_instances() -> None:
        # Failures are logged, not raised: an error escaping a commit callback
        # would break the commit.
        pipeline = _build_pipeline()
        if pipeline is None:
            return
        for queryset in querysets:
            # its extractor's get_queryset() loads the related rows each
            # document reads in the same query, not one query per instance
            extractor = rag.new_extractor(queryset.model)
            for instance in extractor.get_queryset(queryset):
                _sync_instance(pipeline, instance)

    transaction.on_commit(sync_instances)


def _build_pipeline() -> SyncPipeline | None:
    """Return a pipeline to the configured output, or ``None``, logging a failure."""
    try:
        return SyncPipeline(configured_output())
    except Exception:
        logger.exception("Building the output failed")
        return None


def _sync_instance(pipeline: SyncPipeline, instance: Model) -> None:
    """Hand the documents of ``instance`` to the output, logging a failure."""
    try:
        pipeline.run_instance(instance)
    except Exception:
        logger.exception(
            "Syncing %s failed", model_source_key(instance._meta.model, instance.pk)
        )
