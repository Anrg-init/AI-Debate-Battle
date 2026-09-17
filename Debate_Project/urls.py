from django.contrib import admin
from django.urls import path, include
from Debate_app import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path('admin/', admin.site.urls),
    path("", include("Debate_app.urls")),
]
