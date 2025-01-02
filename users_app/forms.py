from django.contrib.auth.forms import UserCreationForm
from users_app.models import UserProfile

class UserProfileCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = UserProfile
        fields = '__all__'