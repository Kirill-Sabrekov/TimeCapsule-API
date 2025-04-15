from django.db import models
from django.contrib.auth.models import User

class Capsule(models.Model):
    text = models.TextField()
    date_open = models.DateTimeField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Capsule by {self.author.username} (open: {self.date_open})"