from django.db import models
from django.contrib.auth.models import AbstractUser


class UserProfile(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(max_length=120, blank=True, null=True)
