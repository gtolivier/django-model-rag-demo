from django.db import models
from django.urls import reverse


class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    def get_absolute_url(self) -> str:
        return reverse("page_detail", kwargs={"slug": self.slug})


class AccordionItem(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()


class TextPlugin(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    body = models.TextField()
