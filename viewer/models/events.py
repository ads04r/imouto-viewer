from django.db import models
from django.db.models import Field, F
from colorfield.fields import ColorField
from polymorphic.models import PolymorphicModel
from dateutil import parser

from viewer.models.core import Event
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class EventSimilarity(models.Model):
	event1 = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="similar_from")
	event2 = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="similar_to")
	diff_value = models.FloatField()
	def __str__(self):
		return "Similarity between " + str(self.event1) + " and " + str(self.event2)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'event similarity'
		verbose_name_plural = 'event similarities'
		indexes = [
			models.Index(fields=['diff_value'])
		]
		constraints = [
			models.UniqueConstraint(fields=['event1', 'event2'], name='events to compare')
		]

class EventWorkoutCategory(models.Model):
	events = models.ManyToManyField(Event, related_name='workout_categories')
	id = models.SlugField(max_length=32, primary_key=True)
	label = models.CharField(max_length=32, default='')
	comment = models.TextField(null=True, blank=True)
	icon = models.SlugField(max_length=64, default='calendar')
	def __set_stat(self, key, value):
		try:
			stat = self.stats.get(label=key)
		except:
			stat = EventWorkoutCategoryStat(label=key, category=self)
		stat.value = str(value)
		stat.save()
		return stat
	def __get_stat(self, stat):
		try:
			v = self.stats.get(label=stat).value
		except:
			v = self.recalculate_stats().get(label=stat).value
		ret = parser.parse(v)
		return ret
	@property
	def tags(self):
		return EventTag.objects.filter(events__workout_categories=self).distinct().exclude(id='')
	@property
	def events_sorted(self):
		return self.events.order_by('-start_time')
	def stats_as_dict(self):
		ret = {}
		for stat in self.stats.all():
			ret[stat.label] = stat.value
		return ret
	def recalculate_stats(self):
		c = self.events.count()
		self.__set_stat('count', c)
		if c > 0:
			events = self.events.all().order_by('start_time')
			self.__set_stat('first_event', events[0].start_time)
			self.__set_stat('last_event', events[c - 1].start_time)
		return self.stats
	@property
	def last_event(self):
		return self.__get_stat('last_event')
	@property
	def first_event(self):
		return self.__get_stat('first_event')
	def __str__(self):
		r = self.id
		if len(self.label) > 0:
			r = self.label
		return(r)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'workout category'
		verbose_name_plural = 'workout categories'

class EventWorkoutCategoryStat(models.Model):
	category = models.ForeignKey(EventWorkoutCategory, related_name='stats', on_delete=models.CASCADE)
	label = models.SlugField(max_length=32)
	value = models.CharField(max_length=255)
	def __str__(self):
		return str(self.category) + ' ' + str(self.label)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'workout category statistic'
		verbose_name_plural = 'workout category statistics'

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
		verbose_name = 'tag workout condition'
		verbose_name_plural = 'tag workout conditions'
