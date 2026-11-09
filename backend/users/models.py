from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)

    # A person can be both. Rename per project (e.g. is_renter / is_owner).
    is_customer = models.BooleanField(default=True)
    is_provider = models.BooleanField(default=False)

    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_customer=True) | models.Q(is_provider=True),
                name="user_has_at_least_one_role",
            )
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
