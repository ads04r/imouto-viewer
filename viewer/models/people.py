from django.db import models
from django.db.models import Field, F
from django.contrib.staticfiles import finders
from colorfield.fields import ColorField
from PIL import Image

from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class Person(models.Model):
	""" This is a class representing a person significant to the user. It must have some kind
	of name, but everything else is pretty much optional. The class can store information such
	as date of birth, photo, home location or, if they are famous enough, their Wikipedia article.
	"""
	uid = models.SlugField(primary_key=True, max_length=32)
	given_name = models.CharField(null=True, blank=True, max_length=128)
	family_name = models.CharField(null=True, blank=True, max_length=128)
	nickname = models.CharField(null=True, blank=True, max_length=128)
	wikipedia = models.URLField(blank=True, null=True)
	image = models.ImageField(blank=True, null=True, upload_to=user_thumbnail_upload_location)
	significant = models.BooleanField(default=True)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {'id': self.uid, 'name': self.name(), 'full_name': self.full_name()}
		if not(self.birthday is None):
			if self.birthday:
				ret['birthday'] = self.birthday.strftime("%Y-%m-%d")
		home = self.home()
		if not(home is None):
			ret['home'] = home.to_dict()
		return ret
	def name(self):
		label = self.nickname
		if ((label == '') or (label is None)):
			label = self.full_name()
		return label
	@property
	def birthday(self):
		bd = self.get_property('birthday')
		if len(bd) == 0:
			return None
		try:
			ret = datetime.datetime.strptime(bd[0], '%Y-%m-%d').date()
		except:
			ret = None
		return ret
	@property
	def next_birthday(self):
		bd = self.get_property('birthday')
		if len(bd) == 0:
			return None
		now = datetime.datetime.now().date()
		dt = datetime.datetime.strptime(str(now.year) + bd[0][4:], '%Y-%m-%d').date()
		while dt < now:
			dt = dt.replace(year=dt.year + 1)
		return dt
	@property
	def age(self):
		bd = self.birthday
		if bd is None:
			return None
		return self.next_birthday.year - bd.year - 1
	def full_name(self):
		label = str(self.given_name) + ' ' + str(self.family_name)
		label = label.strip()
		if label == '':
			label = self.nickname
		return label
	def home(self):
		ret = None
		dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
		for prop in PersonProperty.objects.filter(person=self).filter(key='livesat'):
			value = int(str(prop.value))
			try:
				place = Location.objects.get(pk=value)
			except:
				continue
			if not(place.creation_time is None):
				if place.creation_time > dt:
					continue
			if not(place.destruction_time is None):
				if place.destruction_time < dt:
					continue
			ret = place
		return ret
	def places(self):
		ret = []
		for event in Event.objects.filter(people=self):
			loc = event.location
			if loc is None:
				continue
			if loc in ret:
				continue
			ret.append(loc)
		return ret
	def photo(self):
		im = Image.open(self.image.path)
		return im
	def thumbnail(self, size):
		try:
			im = Image.open(self.image.path)
		except:
			unknown = finders.find('viewer/graphics/unknown_person.jpg')
			if os.path.exists(unknown):
				im = Image.open(unknown)
			else:
				return None
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
	def messages(self):
		ret = []
		for phone in PersonProperty.objects.filter(person=self, key='mobile'):
			for ri in RemoteInteraction.objects.filter(address=phone.value):
				ret.append(ri)
		return sorted(ret, key=lambda k: k.time, reverse=True)
	def get_property(self, key):
		ret = []
		for prop in PersonProperty.objects.filter(person=self).filter(key=key):
			ret.append(str(prop.value))
		return ret
	def get_properties(self):
		ret = []
		for prop in PersonProperty.objects.filter(person=self):
			value = str(prop.key)
			if value in ret:
				continue
			ret.append(value)
		return ret
	def get_stats(self):
		ret = {'events': 0, 'photos': 0, 'places': 0}
		ret['events'] = Event.objects.filter(people=self).count()
		ret['photos'] = Photo.objects.filter(people=self).count()
		ret['places'] = len(self.places())
		try:
			ret['first_met'] = Event.objects.filter(people=self).order_by('start_time')[0].start_time
		except:
			ret['first_met'] = None
		return ret
	def photos(self):
		return Photo.objects.filter(people__in=[self]).order_by('-time')
	def events(self):
		return Event.objects.filter(people=self).order_by('-start_time')
	def __str__(self):
		return self.name()
	class Meta:
		app_label = 'viewer'
		verbose_name = 'person'
		verbose_name_plural = 'people'
		indexes = [
			models.Index(fields=['nickname']),
			models.Index(fields=['given_name', 'family_name']),
		]

class RemoteInteraction(models.Model):
	type = models.SlugField(max_length=32)
	time = models.DateTimeField()
	address = models.CharField(max_length=128)
	incoming = models.BooleanField()
	title = models.CharField(max_length=255, default='', blank=True)
	message = models.TextField(default='', blank=True)
	def person(self):
		address = self.address.replace(' ', '')
		try:
			person = PersonProperty.objects.get(value=address).person
		except:
			person = None
		return person
	def __str__(self):
		if self.incoming:
			label = 'Message from ' + str(self.address)
		else:
			label = 'Message to ' + str(self.address)
		return label
	class Meta:
		app_label = 'viewer'
		verbose_name = 'remote interaction'
		verbose_name_plural = 'remote interactions'
		indexes = [
			models.Index(fields=['type']),
			models.Index(fields=['address']),
			models.Index(fields=['time']),
			models.Index(fields=['title']),
		]

class PersonProperty(models.Model):
	person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="properties")
	key = models.SlugField(max_length=32)
	value = models.CharField(max_length=255)
	def __str__(self):
		return str(self.person) + ' - ' + self.key
	class Meta:
		app_label = 'viewer'
		verbose_name = 'person property'
		verbose_name_plural = 'person properties'
		indexes = [
			models.Index(fields=['person']),
			models.Index(fields=['key']),
		]

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
