import uuid

from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class UploadedData(TimeStampedModel): # Need to plan this model properly later as per requirements.
    pass
        
    