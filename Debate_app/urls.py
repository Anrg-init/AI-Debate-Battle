from django.urls import path
from . import views

urlpatterns = [
    path("", views.home , name="home"),
    path("stream/", views.stream_debate, name="stream"),
    path("upload/", views.upload_document, name="upload_document"),
    path("signup/", views.signup_view, name="signup_view"),
    path("login/", views.login_view, name="login_view"),
    path("logout/", views.logout_view, name="logout"),
    path("history/", views.history_view, name="history"),
    path("history/<str:thread_id>/", views.history_detail_view, name="history_detail"),

    
]


