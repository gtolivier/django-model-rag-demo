from django.db import models
from django.urls import reverse
from django.utils.text import Truncator


class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    language = models.CharField(max_length=8, default="en")

    def get_absolute_url(self) -> str:
        return reverse("page_detail", kwargs={"slug": self.slug})

    def __str__(self) -> str:
        return self.title


class AccordionItem(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()

    def __str__(self) -> str:
        return self.title


class TextPlugin(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    body = models.TextField()

    def __str__(self) -> str:
        return Truncator(self.body).words(8)
