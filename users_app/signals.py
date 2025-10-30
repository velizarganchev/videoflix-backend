"""
users_app.signals — UserProfile signal handlers for Videoflix backend

Purpose:
--------
Automatically create an authentication token for each new user
immediately after a UserProfile instance is saved (created).

This ensures that every registered user has a corresponding DRF Token
without requiring a manual login first.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from .models import UserProfile


@receiver(post_save, sender=UserProfile)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to handle new user creation.

    Triggered:
        After a UserProfile instance is saved (via post_save signal).

    Behavior:
        - If a new user is created, automatically generate
          an authentication Token linked to that user.
    """
    if created:
        Token.objects.create(user=instance)
