from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("stream/", views.stream_debate, name="stream"),
    path("upload/", views.upload_document, name="upload_document"),
    path("signup/", views.signup_view, name="signup_view"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("history-data/", views.history_json, name="history_json"),
    path("history/<str:thread_id>/", views.history_detail_view, name="history_detail"),


    
]


