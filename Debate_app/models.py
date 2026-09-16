from django.db import models
from django.contrib.auth.models import User

class Debate(models.Model):
    thread_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    