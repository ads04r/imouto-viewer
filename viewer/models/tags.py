from django.db import models
from django.core.files import File
from django.db.models import Field, F
from polymorphic.models import PolymorphicModel
from django.conf import settings
from colorfield.fields import ColorField
from PIL import Image
from io import BytesIO
from staticmap import StaticMap, CircleMarker

from viewer.models.places import Location
from viewer.models import Event, EventWorkoutCategory

from viewer.functions.geo import get_location_name
from viewer.functions.location_manager import get_possible_location_events
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class EventTag(models.Model):
	events = models.ManyToManyField(Event, related_name='tags')
	id = models.SlugField(max_length=32, primary_key=True)
	comment = models.TextField(null=True, blank=True)
	colour = ColorField(default='#777777')
	def __str__(self):
		return(self.id)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'event tag'
		verbose_name_plural = 'event tags'

class AutoTag(models.Model):
	""" This class represents a relationship between an EventTag and a collection of
	TagConditions which allows Imouto Viewer to automatically assign tags to Events
	on create/save, if they fulfil a set of conditions.
	"""
	tag = models.ForeignKey(EventTag, null=False, on_delete=models.CASCADE, related_name='rules')
	enabled = models.BooleanField(default=True)
	def add_location_condition(self, lat, lon):
		ret = TagLocationCondition(lat=lat, lon=lon, tag=self)
		ret.save()
		return ret
	def add_type_condition(self, type):
		ret = TagTypeCondition(type=type, tag=self)
		ret.save()
		return ret
	def eval(self, event):
		if not(self.enabled):
			return False
		if self.conditions.count() == 0:
			return False
		for cond in self.conditions.all():
			cond_eval = cond.eval(event)
			if not(cond_eval):
				return False
		return True

	def __str__(self):
		return(str(self.tag))

	class Meta:
		app_label = 'viewer'
		verbose_name = 'autotag'
		verbose_name_plural = 'autotags'

class TagCondition(PolymorphicModel):
	""" This is the base class for all the different kinds of condition that may
	be checked when deciding to automatically assign an EventTag to an Event. It
	relies on django-polymorphic in order to work, as this is the simplest way I
	know of to subclass Django models.
	"""
	tag = models.ForeignKey(AutoTag, null=False, on_delete=models.CASCADE, related_name='conditions')
	def eval(self, event):
		return False

	def __str__(self):
		return(str(self.tag))

	@property
	def description(self):
		return "A general condition"

	class Meta:
		app_label = 'viewer'
		verbose_name = 'tag condition'
		verbose_name_plural = 'tag conditions'

class TagLocationCondition(TagCondition):
	""" A subclass of TagCondition, this checks to see if the user entered the
	vicinity of a particular geographical point (configurable in the Location
	Manager) and assigns its `tag` if so.
	"""
	lat = models.FloatField()
	lon = models.FloatField()
	cached_staticmap = models.ImageField(blank=True, null=True, upload_to=tag_staticmap_upload_location)
	cached_locationtext = models.TextField(default='')
	def eval(self, event):
		for ev in get_possible_location_events(event.start_time.date(), self.lat, self.lon):
			if ((ev['start_time'] > event.start_time) & (ev['end_time'] < event.end_time)):
				return True
		return False

	@property
	def description(self):
		ret = self.location_text()
		if ret == '':
			ret = str(self.lat) + ',' + str(self.lon)
		return "Location near: " + ret

	def staticmap(self):
		if self.cached_staticmap:
			im = Image.open(self.cached_staticmap.path)
			return im
		m = StaticMap(320, 320, url_template=settings.MAP_TILES)
		marker_outline = CircleMarker((self.lon, self.lat), 'white', 18)
		marker = CircleMarker((self.lon, self.lat), '#3C8DBC', 12)
		m.add_marker(marker_outline)
		m.add_marker(marker)
		im = m.render(zoom=17)
		blob = BytesIO()
		im.save(blob, 'PNG')
		self.cached_staticmap.save(tag_staticmap_upload_location, File(blob), save=False)
		self.save()
		return im

	def location_text(self):
		if self.cached_locationtext != '':
			return self.cached_locationtext
		ret = get_location_name(self.lat, self.lon)
		if ret != '':
			self.cached_locationtext = ret
			self.save()
		return ret

	def __str__(self):
		return(str(self.tag))

	class Meta:
		app_label = 'viewer'
		verbose_name = 'tag location condition'
		verbose_name_plural = 'tag location conditions'

class TagTypeCondition(TagCondition):
	""" A subclass of TagCondition, this checks to see if an Event is of
	a particular `type`, and assigns its `tag` if so.
	"""
	type = models.SlugField(max_length=32)
	def eval(self, event):
		if event.type == self.type:
			return True
		return False

	@property
	def description(self):
		return "Event type: " + str(self.type)

	def __str__(self):
		return(str(self.tag))

	class Meta:
		app_label = 'viewer'
		verbose_name = 'tag type condition'
		verbose_name_plural = 'tag type conditions'

class TagWorkoutCondition(TagCondition):
	""" A subclass of TagCondition, this checks to see if an Event is linked
	to a particular EventWorkoutCategory, and assigns its `tag` if so. Handy
	if you tag your journeys with the method of transportation, for example,
	you can have the tag 'cycling' be created if the user was on a bike.
	"""
	workout_category = models.ForeignKey(EventWorkoutCategory, null=False, on_delete=models.CASCADE)
	def eval(self, event):
		if self.workout_category in event.workout_categories.all():
			return True
		return False

	@property
	def description(self):
		return "Workout category: " + str(self.workout_category)

	def __str__(self):
		return(str(self.tag))

	class Meta:
		app_label = 'viewer'
		verbose_name = 'tag workour condition'
		verbose_name_plural = 'tag workout conditions'

