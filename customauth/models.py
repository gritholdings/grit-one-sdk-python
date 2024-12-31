import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    email = models.EmailField(verbose_name='email address', unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'  # Set email as the unique identifier
    REQUIRED_FIELDS = []  # Remove username from REQUIRED_FIELDS

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Initialize metadata as an empty dict if it's None
        if self.metadata is None:
            self.metadata = {}
        super().save(*args, **kwargs)