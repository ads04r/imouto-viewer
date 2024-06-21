from django.db import models

import logging
logger = logging.getLogger(__name__)

class Media(models.Model):
	type = models.SlugField(max_length=16)
	unique_id = models.SlugField(max_length=128)
	label = models.CharField(max_length=255)

class MediaEvent(models.Model):
	media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="events")
	time = models.DateTimeField()
