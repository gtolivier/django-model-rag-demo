"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path

from blog.views import article_detail, article_list
from catalog.views import product_detail, product_list
from pages.views import home, page_detail

urlpatterns = [
    path("admin/", admin.site.urls),
    path("pages/<slug:slug>/", page_detail, name="page_detail"),
]

urlpatterns += i18n_patterns(
    path("", home, name="home"),
    path("blog/", article_list, name="article_list"),
    path("blog/<int:pk>/", article_detail, name="article_detail"),
    path("products/", product_list, name="product_list"),
    path("products/<int:pk>/", product_detail, name="product_detail"),
    prefix_default_language=False,
)
