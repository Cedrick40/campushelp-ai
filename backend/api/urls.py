from django.urls import path
from . import views
urlpatterns = [
    path("health/", views.health),
    path("ask/", views.ask),
    path("corpus/", views.corpus),
    path("documents/<str:pk>/file/", views.document_file),
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/logout/", views.logout),
    path("auth/me/", views.me),
    path("history/", views.history),
    path("history/<int:pk>/", views.history_detail),
]
