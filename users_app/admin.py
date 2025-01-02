from django.contrib import admin
from users_app.models import UserProfile
from users_app.forms import UserProfileCreationForm
from django.contrib.auth.admin import UserAdmin


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    add_form = UserProfileCreationForm
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            'Additional Info',
            {
                'fields': (
                    'phone',
                    'address',
                )
            }
        )
    )
