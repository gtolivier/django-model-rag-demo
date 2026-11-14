from django.db import models
from django.urls import reverse
from django.utils.translation import override


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    language = models.CharField(max_length=8, default="en")

    def get_absolute_url(self) -> str:
        with override(self.language):
            return reverse("product_detail", kwargs={"pk": self.pk})

    def __str__(self) -> str:
        return self.name
