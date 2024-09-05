from django.db import models

from viewer.models.core import WeatherLocation

import logging
logger = logging.getLogger(__name__)

class WeatherReading(models.Model):
	time = models.DateTimeField()
	location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, related_name='readings')
	description = models.CharField(max_length=128, blank=True, null=True)
	temperature = models.FloatField(blank=True, null=True)
	wind_speed = models.FloatField(blank=True, null=True)
	wind_direction = models.IntegerField(blank=True, null=True)
	humidity = models.IntegerField(blank=True, null=True)
	visibility = models.IntegerField(blank=True, null=True)
	def __str__(self):
		return str(self.time) + ' at ' + str(self.location)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'weather reading'
		verbose_name_plural = 'weather readings'


