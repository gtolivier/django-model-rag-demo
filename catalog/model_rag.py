from django_model_rag import rag

from catalog.models import Product

rag.register(
    Product,
    fields=["name", "description"],
    title_field="name",
    follow=["category"],
)
