from django.db import models
from django.urls import reverse


class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()

    def get_absolute_url(self) -> str:
        return reverse("article_detail", kwargs={"pk": self.pk})
