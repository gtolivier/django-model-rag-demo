from django_model_rag import rag

from blog.models import Article

rag.register(Article)
