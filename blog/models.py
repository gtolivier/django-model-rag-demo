from django.db import models
from django.urls import reverse
from django.utils.translation import override


class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    language = models.CharField(max_length=8, default="en")

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        with override(self.language):
            return reverse("article_detail", kwargs={"pk": self.pk})
