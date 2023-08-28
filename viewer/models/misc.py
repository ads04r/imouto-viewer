from django.db import models
from django.db.models import Field, IntegerField, F

from viewer.models.places import Location

from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class DataReading(models.Model):
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	type = models.SlugField(max_length=32)
	value = models.IntegerField()
	def length(self):
		return((self.end_time - self.start_time).total_seconds())
	def __str__(self):
		return str(self.type) + "/" + str(self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
	class Meta:
		app_label = 'viewer'
		verbose_name = 'data reading'
		verbose_name_plural = 'data readings'
		indexes = [
			models.Index(fields=['start_time']),
			models.Index(fields=['end_time']),
			models.Index(fields=['type']),
		]

class CalendarFeed(models.Model):
	url = models.URLField()
	def __str__(self):
		return(str(self.url))
	class Meta:
		app_label = 'viewer'
		verbose_name = 'calendar'
		verbose_name_plural = 'calendars'

class CalendarAppointment(models.Model):
	eventid = models.SlugField(max_length=255, blank=True, default='', unique=True)
	start_time = models.DateTimeField()
	end_time = models.DateTimeField(null=True, blank=True)
	all_day = models.BooleanField(default=False)
	data = models.TextField(default='', blank=True)
	location = models.ForeignKey(Location, on_delete=models.SET_NULL, related_name="appointments", null=True, blank=True)
	caption = models.CharField(max_length=255, default='', blank=True)
	description = models.TextField(default='', blank=True)
	created_time = models.DateTimeField(auto_now_add=True)
	updated_time = models.DateTimeField(auto_now=True)
	calendar = models.ForeignKey(CalendarFeed, on_delete=models.CASCADE, related_name='events')
	def __str__(self):
		return(self.eventid)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'calendar appointment'
		verbose_name_plural = 'calendar appointments'
