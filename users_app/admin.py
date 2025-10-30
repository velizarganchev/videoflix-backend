"""
users_app.admin — Django admin configuration for UserProfile

Extends Django’s built-in UserAdmin with additional fields
and a custom user creation form.

Includes:
- Custom form for creating users via admin interface
- Extra profile information (phone, address, favorite videos)
"""

from django.contrib import admin
from users_app.models import UserProfile
from users_app.forms import UserProfileCreationForm
from django.contrib.auth.admin import UserAdmin


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the custom UserProfile model.

    Extends default UserAdmin with:
    - Custom creation form (UserProfileCreationForm)
    - Additional fields for contact info and favorites
    """

    add_form = UserProfileCreationForm

    # Extend base fieldsets from Django's UserAdmin with custom section
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "Additional Info",
            {
                "fields": (
                    "phone",
                    "address",
                    "favorite_videos",
                )
            },
        ),
    )
