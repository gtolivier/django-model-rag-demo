from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django_model_rag import SyncPipeline, rag
from django_model_rag.output import configured_output


def sync_on_commit(*querysets: QuerySet[Any]) -> None:
    """Hand the documents of the instances of ``querysets`` to the output at commit.

    For instances whose documents carry the fields of another model: the
    package syncs an instance on its own save, not on the save of what it reads.
    """

    def sync_instances() -> None:
        pipeline = SyncPipeline(configured_output())
        for queryset in querysets:
            # its extractor's get_queryset() loads the related rows each
            # document reads in the same query, not one query per instance
            extractor = rag.new_extractor(queryset.model)
            for instance in extractor.get_queryset(queryset):
                pipeline.run_instance(instance)

    transaction.on_commit(sync_instances)
