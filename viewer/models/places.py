from django.db import models
from django.db.models import Count, Avg, Field, IntegerField, F, ExpressionWrapper
from django.db.models.fields import DurationField
from django.conf import settings
from colorfield.fields import ColorField
from PIL import Image

from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class WeatherLocation(models.Model):
	id = models.SlugField(max_length=32, primary_key=True)
	lat = models.FloatField()
	lon = models.FloatField()
	api_id = models.SlugField(max_length=32, default='')
	label = models.CharField(max_length=64)
	def __str__(self):
		return str(self.label)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'weather location'
		verbose_name_plural = 'weather locations'
		indexes = [
			models.Index(fields=['label'])
		]

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

class LocationCountry(models.Model):
	a2 = models.SlugField(primary_key=True, max_length=2)
	a3 = models.SlugField(unique=True, max_length=3)
	label = models.CharField(max_length=100)
	wikipedia = models.URLField(blank=True, null=True)
	def __str__(self):
		return str(self.label)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {'iso': [self.a2, self.a3], "label": str(self.label)}
		if self.wikipedia:
			ret['wikipedia'] = str(self.wikipedia)
		return ret
	class Meta:
		app_label = 'viewer'
		verbose_name = 'country'
		verbose_name_plural = 'countries'

class Location(models.Model):
	"""This is a class representing a named location significant to the user. It does not need to be validated by any
	authority, but must have a name, a latitude and longitude, and a country (represented by the LocationCountry class)
	It may optionally have other properties, such as an address, phone number, Wikipedia article or photo depiction.
	"""
	uid = models.SlugField(unique=True, max_length=32)
	label = models.CharField(max_length=100)
	full_label = models.CharField(max_length=200, default='')
	description = models.TextField(blank=True, null=True)
	lat = models.FloatField()
	lon = models.FloatField()
	country = models.ForeignKey(LocationCountry, related_name='locations', null=True, blank=True, on_delete=models.SET_NULL)
	creation_time = models.DateTimeField(blank=True, null=True)
	destruction_time = models.DateTimeField(blank=True, null=True)
	address = models.TextField(blank=True, null=True)
	phone = models.CharField(max_length=20, blank=True, null=True)
	url = models.URLField(blank=True, null=True)
	wikipedia = models.URLField(blank=True, null=True)
	image = models.ImageField(blank=True, null=True, upload_to=location_thumbnail_upload_location)
	weather_location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, null=True, blank=True)
	@property
	def is_home(self):
		"""
		Determines if this Location is the user's home or not. Always returns False if USER_HOME_LOCATION is not set in settings.py
		"""
		try:
			home = settings.USER_HOME_LOCATION
		except:
			home = -1
		return (self.pk == home)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {'id': self.uid, 'label': self.label, 'full_label': self.full_label, 'lat': self.lat, 'lon': self.lon}
		if not(self.description is None):
			if self.description != '':
				ret['description'] = self.description
		if not(self.address is None):
			if self.address != '':
				ret['address'] = self.address
		if not(self.url is None):
			if self.url != '':
				ret['url'] = self.url
		return ret
	def people(self):
		"""
		Returns a list of people who have been encountered at this location in the past.

		:return: A list of Person objects.
		:rtype: list
		"""
		ret = []
		for event in self.events.all():
			for person in event.people.all():
				if person in ret:
					continue
				ret.append(person)
		return ret
	def geo(self):
		"""
		Useful for drawing straight onto a Leaflet map, this function returns the geographical location of the Location as a GeoJSON object.

		:return: A GeoJSON object.
		:rtype: dict
		"""
		point = {}
		point['type'] = "Point"
		point['coordinates'] = [self.lon, self.lat]
		ret = {}
		ret['type'] = "Feature"
		ret['bbox'] = [self.lon - 0.0025, self.lat - 0.0025, self.lon + 0.0025, self.lat + 0.0025]
		ret['properties'] = {}
		ret['geometry'] = point
		return json.dumps(ret);
	def photo(self):
		"""
		Returns an image of the Location as a Pillow Image object.

		:return: An image of the location, if one exists
		:rtype: Image
		"""
		im = Image.open(self.image.path)
		return im
	def allphotos(self):
		"""
		Returns all the Photo objects associated with this Location.

		:return: A list of Photo objects
		:rtype: list
		"""
		ret = []
		for photo in Photo.objects.filter(location=self):
			ret.append(photo)
		for event in Event.objects.filter(location=self):
			for photo in event.photos():
				ret.append(photo)
		return ret
	def thumbnail(self, size):
		"""
		Returns a thumbnail of the image of this Location, as a Pillow object.

		:param size: The size (in pixels) of the returned object (always a square).
		:return: A small image, as a Pillow object.
		:rtype: Image
		"""
		im = Image.open(self.image.path)
		bbox = im.getbbox()
		w = bbox[2]
		h = bbox[3]
		if h > w:
			ret = im.crop((0, 0, w, w))
		else:
			x = int((w - h) / 2)
			ret = im.crop((x, 0, x + h, h))
		ret = ret.resize((size, size), 1)
		return ret
	def get_property(self, key):
		"""
		Takes a simple string as an argument, and returns a list of strings representing the values related to this Location via that property name.

		:param key: A string representing a property.
		:return: The value(s) of the specified property, as a list of strings.
		:rtype: list
		"""
		ret = []
		for prop in LocationProperty.objects.filter(location=self).filter(key=key):
			ret.append(str(prop.value))
		return ret
	def get_properties(self):
		"""
		Gets all the valid property keys for this Location as a list of strings, which can each then be sent to `get_property` in order to get the relevant value(s).

		:return: All the properties that have been assigned to this particular Location.
		:rtype: list
		"""
		ret = []
		for prop in LocationProperty.objects.filter(location=self):
			value = str(prop.key)
			if value in ret:
				continue
			ret.append(value)
		return ret
	def exists(self):
		"""
		Determines whether or not this Location currently exists (eg has been built, and has not been demolished.)

		:return: True normally, False if the Location has not yet been built, or has been destroyed.
		:rtype: bool
		"""
		dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
		if((self.destruction_time is None) & (self.creation_time is None)):
			return True
		if(not(self.destruction_time is None)):
			if dt > self.destruction_time:
				return False
		if(not(self.creation_time is None)):
			if dt < self.creation_time:
				return False
		return True
	def tags(self):
		"""
		Returns all the EventTags that have been assigned to Events taking place within this Location.

		:return: A queryset of EventTags
		:rtype: Queryset(EventTag)
		"""
		return EventTag.objects.filter(events__location=self).distinct().exclude(id='')
	def add_category(self, catname):
		"""
		Adds a category to a Location, from a string value. The category is created if it doesn't exist.

		:param tagname: The name of the category to add
		"""
		catid = str(catname)
		try:
			category = LocationCategory.objects.get(caption__iexact=catid)
		except:
			category = LocationCategory(caption=catid, colour=('#' + str("%06x" % random.randint(0, 0xFFFFFF)).upper()))
			category.save()
		self.categories.add(category)
	def longest_event(self):
		"""
		Looks for the longest Event taking place in this Location and returns its duration.

		:return: A timedelta, the duration of the longest Event object.
		:rtype: datetime.timedelta
		"""
		duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
		try:
			ret = Event.objects.filter(location=self).exclude(type='life_event').annotate(duration=duration).order_by('-duration')[0].duration
		except:
			ret = datetime.timedelta(hours=0)
		return ret
	def average_event(self):
		"""
		Calculates the mean average duration of all the Events that have taken place at this Location.

		:return: A timedelta representing the mean average time
		:rtype: datetime.timedelta
		"""
		duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
		try:
			ret = Event.objects.filter(location=self).exclude(type='life_event').annotate(duration=duration).aggregate(av=Avg('duration'))['av']
		except:
			ret = datetime.timedelta(hours=0)
		if ret is None:
			ret = datetime.timedelta(hours=0)
		return datetime.timedelta(seconds=int(ret.total_seconds()))
	def weekdays(self):
		"""
		Calculates the number of days spent in this particular Location, grouped by day of the week.

		:return: A dict, for passing to Graph.js
		:rtype: dict
		"""
		ret = {'days': [], 'values': []}
		d = ['', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
		for item in Event.objects.filter(location=self).exclude(type='life_event').values('start_time__wd').annotate(ct=Count('start_time__wd')).order_by('start_time__wd'):
			id = item['start_time__wd']
			ret['days'].append(d[id])
			ret['values'].append(item['ct'])
		ret['json'] = json.dumps(ret['days'])
		return ret
	def __str__(self):
		label = self.label
		if self.full_label != '':
			label = self.full_label
		return label
	class Meta:
		app_label = 'viewer'
		verbose_name = 'location'
		verbose_name_plural = 'locations'
		indexes = [
			models.Index(fields=['label']),
			models.Index(fields=['full_label']),
		]

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

class LocationCategory(models.Model):
	"""This class represents a category of places. It should normally be used
	for things like 'pub' and 'cinema' but can also be 'friends houses', etc.
	"""
	caption = models.CharField(max_length=255, default='', blank=True)
	locations = models.ManyToManyField(Location, related_name='categories')
	colour = ColorField(default='#777777')
	parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name="children", null=True, blank=True)
	def __str__(self):
		return(self.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'location category'
		verbose_name_plural = 'location categories'
