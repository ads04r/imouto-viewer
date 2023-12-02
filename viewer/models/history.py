from django.db import models
import datetime

class HistoricalEvent(models.Model):
	date = models.DateField()
	"""The date thie HistoricalEvent happened"""
	category = models.SlugField(max_length=32)
	"""The type or category of this HistoricalEvent. This is a string and can be anything you like"""
	description = models.TextField()
	@property
	def years_ago(self):
		now = datetime.datetime.now().date()
		return now.year - self.date.year
	def __str__(self):
		return self.description
	class Meta:
		verbose_name = "historical event"
		verbose_name_plural = "historical events"

