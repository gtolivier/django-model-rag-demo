from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_model_rag import rag

from catalog.models import Category, Product
from config.rag_sync import sync_on_commit

rag.register(
    Product,
    fields=["name", "description"],
    title_field="name",
    follow=["category"],
)


@receiver(post_save, sender=Category)
def sync_products_of_saved_category(
    sender: type[Category],
    instance: Category,
    created: bool = False,
    raw: bool = False,
    **kwargs: Any,
) -> None:
    # the products' documents carry the category's name. A new category has no
    # products yet: each one added later syncs on its own save.
    if raw or created:
        return

    sync_on_commit(Product.objects.filter(category=instance.pk))
