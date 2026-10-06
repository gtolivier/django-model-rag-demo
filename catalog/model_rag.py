from typing import Any

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_model_rag import SyncPipeline, rag
from django_model_rag.output import configured_output

from catalog.models import Category, Product

rag.register(
    Product,
    fields=["name", "description"],
    title_field="name",
    follow=["category"],
)


@receiver(post_save, sender=Category)
def sync_products_of_saved_category(
    sender: type[Category], instance: Category, raw: bool = False, **kwargs: Any
) -> None:
    # the products' documents carry the category's name
    if raw:
        return

    def sync_products() -> None:
        pipeline = SyncPipeline(configured_output())
        for product in Product.objects.filter(category=instance.pk):
            pipeline.run_instance(product)

    transaction.on_commit(sync_products)
