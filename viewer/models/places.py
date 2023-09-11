from django.db import models
from django.db.models import Field, IntegerField, F
from colorfield.fields import ColorField

from viewer.models.core import Location, WeatherLocation

import random, datetime, pytz, json, markdown, re, os, urllib.request

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

class LocationProperty(models.Model):
	location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="properties")
	key = models.SlugField(max_length=32)
	value = models.CharField(max_length=255)
	def __str__(self):
		return str(self.location) + ' - ' + self.key
	class Meta:
		app_label = 'viewer'
		verbose_name = 'location property'
		verbose_name_plural = 'location properties'
		indexes = [
			models.Index(fields=['location']),
			models.Index(fields=['key']),
		]

