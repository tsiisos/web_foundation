from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "is_customer", "is_provider")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
