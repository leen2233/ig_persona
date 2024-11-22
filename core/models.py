from django.db import models
from django.contrib.auth import get_user_model


class Persona(models.Model):
    user = models.OneToOneField(get_user_model(), related_name="persona", on_delete=models.CASCADE)
    biography = models.TextField()
    character = models.TextField(blank=True, null=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    avatar = models.ImageField(upload_to='avatars/')
    last_updated = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.username

class ScheduledPost(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    caption = models.TextField()
    image = models.ImageField(upload_to='posts/')
    time = models.DateTimeField()

    def __str__(self):
        return f'{self.persona.username} - {self.time}'
