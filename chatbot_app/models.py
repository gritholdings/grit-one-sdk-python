from django.db import models


class Prompt(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived')
    )

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    internal_note = models.TextField(blank=True)

    def __str__(self):
        return self.name
