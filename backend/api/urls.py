from django.urls import path

from . import views

urlpatterns = [
    path("ask/", views.ask),
    path("corpus/", views.corpus),
    path("documents/<int:pk>/file/", views.document_file),
]