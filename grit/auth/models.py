import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    email = models.EmailField(verbose_name='email address', unique=True)
    is_email_verified =  models.BooleanField(default=False)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    profile = models.ForeignKey( 'Profile',
        on_delete=models.DO_NOTHING, related_name='users',
        null=True, blank=True)
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    def __str__(self):
        return self.email
    def save(self, *args, **kwargs):
        if self.metadata is None:
            self.metadata = {}
        super().save(*args, **kwargs)


class Profile(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name


class UserSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SIGNED_OUT = "signed_out", "Signed out"
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sessions'
    )
    metadata = models.JSONField(blank=True, null=True)
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    user_agent = models.CharField(max_length=512, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ACTIVE
    )
    last_active_at = models.DateTimeField(null=True, blank=True)
    signed_out_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-last_active_at']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
    def __str__(self):
        return f"{self.user.email} — {self.session_key[:8]}"
    def sign_out(self):
        from django.contrib.sessions.backends.db import SessionStore
        SessionStore(session_key=self.session_key).delete()
        self.status = self.Status.SIGNED_OUT
        self.signed_out_at = timezone.now()
        self.save(update_fields=['status', 'signed_out_at', 'updated_at'])


class MFADevice(models.Model):
    class MFAMethod(models.TextChoices):
        EMAIL = 'email', 'Email OTP'
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mfa_devices')
    name = models.CharField(max_length=255, default='Authenticator App')
    method = models.CharField(max_length=10, choices=MFAMethod.choices, default=MFAMethod.EMAIL)
    is_active = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)


class BackupCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=255)
    is_used = models.BooleanField(default=False)
