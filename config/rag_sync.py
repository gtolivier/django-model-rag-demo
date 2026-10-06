import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Model, QuerySet
from django_model_rag import SyncPipeline, rag
from django_model_rag.output import configured_output

logger = logging.getLogger("django_model_rag")


def sync_on_commit(*querysets: QuerySet[Any]) -> None:
    """Hand the documents of the instances of ``querysets`` to the output at commit.

    For instances whose documents carry the fields of another model: the
    package syncs an instance on its own save, not on the save of what it reads.
    """
    if not getattr(settings, "MODEL_RAG_SIGNALS", True):
        return

    def sync_instances() -> None:
        pipeline = SyncPipeline(configured_output())
        for queryset in querysets:
            # its extractor's get_queryset() loads the related rows each
            # document reads in the same query, not one query per instance
            extractor = rag.new_extractor(queryset.model)
            for instance in extractor.get_queryset(queryset):
                _sync_instance(pipeline, instance)

    transaction.on_commit(sync_instances)


def _sync_instance(pipeline: SyncPipeline, instance: Model) -> None:
    """Hand the documents of ``instance`` to the output, logging a failure."""
    try:
        pipeline.run_instance(instance)
    except Exception:
        # An error escaping a commit callback would break the commit.
        logger.exception("Syncing %s failed", instance)
