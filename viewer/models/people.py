from django.db import models
from django.contrib.auth.models import User
from colorfield.fields import ColorField

from viewer.models.core import Person

import logging
logger = logging.getLogger(__name__)

class PersonCategory(models.Model):
	"""This class represents a category of people. It can be something simple
	like 'work colleagues' and 'friends' or it can be more specific, such as
	'people I met at an anime con in 1996'.
	"""
	caption = models.CharField(max_length=255, default='', blank=True)
	people = models.ManyToManyField(Person, related_name='categories')
	colour = ColorField(default='#777777')
	def __str__(self):
		return(self.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'person category'
		verbose_name_plural = 'person categories'
