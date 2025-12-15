from django.db import models
from django.conf import settings
from grit.db.models import BaseModel


class LeadManager(models.Manager):
    def create_with_metadata(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        message: str | None = None
    ):
        lead = self.model(
            first_name=first_name,
            last_name=last_name,
            email=email,
            metadata = {}
        )

        # Add metadata fields
        if phone:
            lead.metadata['phone'] = phone
        if company:
            lead.metadata['company'] = company
        lead.metadata['status'] = {
            "label": "New",
            "value": "new"
        }
        if message:
            lead.metadata['message'] = message

        lead.save()
        return lead


class Lead(BaseModel):
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    # metadata fields:
    # "phone": "string"
    # "company": "string"
    # status: ({"label": "New", "value": "new"}, {"label": "Unqualified", "value": "unqualified"}),
    # "message": "string"
    objects = LeadManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

class Contact(BaseModel):
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    # disable related_name for user field because clashes with owner
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, blank=True,
                    null=True, related_name='+')
    account = models.ForeignKey(
        'Account', on_delete=models.DO_NOTHING, related_name='contacts', null=True, blank=True
    )
    # metadata fields:
    # status: ({"label": "Active", "value": "active"}, {"label": "Inactive", "value": "inactive"},
    #   {"label": "Do Not Contact", "value": "do_not_contact"})

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

class Account(BaseModel):
    name = models.CharField(max_length=255, blank=True)
    # metadata fields:
    # status: ({"label": "Active", "value": "active"}, {"label": "Inactive", "value": "inactive"})

    def __str__(self):
        return self.name