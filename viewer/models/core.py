from django.db import models
from django.core.files import File
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Count, Avg, Max, Sum, Transform, Field, IntegerField, F, ExpressionWrapper
from django.db.models.signals import pre_save
from django.db.models.fields import DurationField
from django.contrib.staticfiles import finders
from django.conf import settings
from django.dispatch import receiver
from django.utils.html import strip_tags
from polymorphic.models import PolymorphicModel
from colorfield.fields import ColorField
from PIL import Image
from io import BytesIO
from wordcloud import WordCloud, STOPWORDS
from configparser import ConfigParser
from staticmap import StaticMap, Line
from dateutil import parser
from xml.dom import minidom
from tzfpy import get_tz
from suntimes import SunTimes

from viewer.health import parse_sleep, max_heart_rate
from viewer.functions.geo import get_location_name
from viewer.functions.location_manager import get_possible_location_events, get_logged_position, getgeoline, getelevation, getspeed, getboundingbox
from viewer.staticcharts import generate_pie_chart, generate_donut_chart
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, overpy, holidays

@Field.register_lookup
class WeekdayLookup(Transform):
	lookup_name = 'wd'
	function = 'DAYOFWEEK'
	@property
	def output_field(self):
		return IntegerField()

def create_or_get_day(query_date):

	dt = None
	if isinstance(query_date, datetime.datetime):
		dt = query_date.date()
	if isinstance(query_date, datetime.date):
		dt = query_date
	if dt > datetime.datetime.now().date():
		return None
	try:
		ret = Day.objects.get(date=dt)
	except:
		ret = Day(date=dt)
		ret.save()

	return ret

def create_or_get_month(month, year):

	if month < 1:
		return None
	if month > 12:
		return None
	try:
		ret = Month.objects.get(year=year, month=month)
	except:
		ret = Month(year=year, month=month)
		ret.save()

	return ret

class GitCommit(models.Model):
	repo_url = models.URLField()
	commit_date = models.DateTimeField()
	hash = models.SlugField(max_length=48, unique=True)
	comment = models.TextField()
	additions = models.IntegerField(blank=True, null=True)
	deletions = models.IntegerField(blank=True, null=True)
	def __str__(self):
		return str(self.hash)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'git commit'
		verbose_name_plural = 'git commits'

class LocationCountry(models.Model):
	a2 = models.SlugField(primary_key=True, max_length=2)
	a3 = models.SlugField(max_length=3, blank=True, null=True)
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
		ret = {'iso': [self.a2], "label": str(self.label)}
		if self.a3:
			ret['iso'].append(self.a3)
		if self.wikipedia:
			ret['wikipedia'] = str(self.wikipedia)
		return ret
	def refresh_cities(self):
		"""
		Calls the OSM Overpass API to determine all the cities within the country specified, and stores them in Imouto.

		:return: A QuerySet of cities linked to this country, after the refresh
		:rtype: QuerySet
		"""
		api = overpy.Overpass()
		query = 'area["name:en"="' + self.label + '"]->.country;node[place=city](area.country);out;'
		result = api.query(query)
		for node in result.nodes:
			if not('name:en' in node.tags):
				continue
			city_name = node.tags['name:en']
			lat = node.lat
			lon = node.lon
			wikipedia = ''
			if 'wikipedia' in node.tags:
				parse = node.tags['wikipedia'].split(':')
				wikipedia = "https://" + parse[0] + ".wikipedia.org/wiki/" + parse[1]
			if not('en.wikipedia.org') in wikipedia:
				wikipedia = ''
			try:
				city = LocationCity.objects.get(label=city_name)
			except:
				city = LocationCity(label=city_name, country=self, lat=lat, lon=lon)
			if city.wikipedia is None:
				if len(wikipedia) > 0:
					city.wikipedia = wikipedia
			try:
				city.save()
			except:
				continue
		return LocationCity.objects.filter(country=self)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'country'
		verbose_name_plural = 'countries'

class LocationCity(models.Model):
	label = models.CharField(max_length=100)
	lat = models.FloatField()
	lon = models.FloatField()
	country = models.ForeignKey(LocationCountry, related_name='cities', null=True, blank=True, on_delete=models.SET_NULL)
	wikipedia = models.URLField(blank=True, null=True)
	def __str__(self):
		return str(self.label)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {"label": str(self.label), "lat": self.lat, "lon": self.lon}
		if self.wikipedia:
			ret['wikipedia'] = str(self.wikipedia)
		if self.country:
			ret['country'] = self.country.to_dict()
		return ret
	class Meta:
		app_label = 'viewer'
		verbose_name = 'city'
		verbose_name_plural = 'cities'

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

class SchemaOrgClass(models.Model):
	label = models.CharField(max_length=256, null=False)
	uri = models.URLField(null=False)
	parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
	comment = models.TextField()
	@property
	def ancestors(self):
		ret = []
		p = self
		while True:
			if p.parent is None:
				break
			if p.parent.label == 'Thing':
				break
			ret.append(p.parent.pk)
			p = p.parent
		return SchemaOrgClass.objects.filter(pk__in=ret).order_by('label')
	def __str__(self):
		return self.label
	class Meta:
		verbose_name = "schema.org class"
		verbose_name_plural = "schema.org classes"

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
	city = models.ForeignKey(LocationCity, related_name='locations', null=True, blank=True, on_delete=models.SET_NULL)
	creation_time = models.DateTimeField(blank=True, null=True)
	destruction_time = models.DateTimeField(blank=True, null=True)
	address = models.TextField(blank=True, null=True)
	phone = models.CharField(max_length=20, blank=True, null=True)
	url = models.URLField(blank=True, null=True)
	wikipedia = models.URLField(blank=True, null=True)
	image = models.ImageField(blank=True, null=True, upload_to=location_thumbnail_upload_location)
	weather_location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, null=True, blank=True)
	parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name="children", null=True, blank=True)
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
	def schema_classes(self):
		ret = []
		for c in self.categories.all():
			if c.schema_map is None:
				continue
			if c.schema_map in ret:
				continue
			ret.append(c.schema_map)
			for sc in c.schema_map.ancestors.all():
				if sc in ret:
					continue
				ret.append(sc)
		return ret
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
		dt = pytz.utc.localize(datetime.datetime.utcnow())
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
		dt = pytz.utc.localize(datetime.datetime.utcnow())
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
	def first_month(self, year):
		dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year, 1, 1, 0, 0, 0))
		dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year, 12, 31, 23, 59, 59))
		event = Event.objects.filter(people=self, end_time__gte=dts, start_time__lte=dte).order_by('start_time').first()
		return int(event.start_time.month)
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

class Photo(models.Model):
	""" A class representing a photo taken by the user. The photos may be simply displayed by
	Imouto's UI, or used for analysis. For example, if the user uses Picasa or Digikam and
	tags their friends' faces in their photos, then it may be inferred that events during which
	the photos were taken involved those people.
	"""
	file = models.FileField(max_length=255)
	time = models.DateTimeField(null=True, blank=True)
	lat = models.FloatField(null=True, blank=True)
	lon = models.FloatField(null=True, blank=True)
	caption = models.CharField(max_length=255, default='', blank=True)
	people = models.ManyToManyField(Person, through='PersonPhoto')
	location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.CASCADE, related_name="photos")
	cached_thumbnail = models.ImageField(blank=True, null=True, upload_to=photo_thumbnail_upload_location)
	face_count = models.IntegerField(null=True, blank=True)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {}
		ret['lat'] = self.lat
		ret['lon'] = self.lon
		ret['filename'] = str(self.file)
		ret['caption'] = str(self.caption)
		if ret['caption'] == '':
			ret['caption'] = str(self.generate_caption())
		ret['date'] = None
		if self.time:
			ret['date'] = self.time.strftime("%Y-%m-%d %H:%M:%S %z")
		ret['people'] = []
		for person in self.people.all():
			ret['people'].append(person.to_dict())
		return ret
	def picasa_info(self):
		image_path = str(self.file.path)
		parsed = os.path.split(image_path)
		picasa_path = os.path.join(parsed[0], 'picasa.ini')
		if not(os.path.exists(picasa_path)):
			picasa_path = os.path.join(parsed[0], '.picasa.ini')
		if not(os.path.exists(picasa_path)):
			return {}
		ret = {}
		cfg = ConfigParser()
		try:
			cfg.read(picasa_path)
		except:
			pass
		ret['ini_filename'] = picasa_path
		if 'Picasa' in cfg:
			ret['directory'] = {}
			for k in cfg['Picasa']:
				try:
					ret['directory'][k] = cfg['Picasa'][k]
				except:
					pass
		ret['filename'] = parsed[1]
		fn = parsed[1]
		if fn in cfg:
			cfgcat = cfg[fn]
			for k in cfgcat:
				try:
					v = cfgcat[k]
				except:
					continue
				if k == 'rotate':
					ret[k] = (int(v.replace('rotate(', '').replace(')', '')) * 90)
					continue
				if k == 'faces':
					ret[k] = v.split(';')
					continue
				if k == 'filters':
					vv = []
					for vi in v.split(';'):
						if '=' in vi:
							vv.append(vi.split('='))
					ret[k] = vv
					continue
				ret[k] = v
		return ret
	def image(self):
		image_path = str(self.file.path)
		picasa_info = self.picasa_info()
		im = Image.open(image_path)
		if hasattr(im, '_getexif'):
			orientation = 0x0112
			exif = im._getexif()
			if exif is not None:
				if orientation in exif:
					orientation = exif[orientation]
					rotations = {
						3: Image.ROTATE_180,
						6: Image.ROTATE_270,
						8: Image.ROTATE_90
					}
					if orientation in rotations:
						im = im.transpose(rotations[orientation])
		if 'rotate' in picasa_info:
			deg = picasa_info['rotate']
			if deg == 270:
				im = im.transpose(Image.ROTATE_90)
			if deg == 180:
				im = im.transpose(Image.ROTATE_180)
			if deg == 90:
				im = im.transpose(Image.ROTATE_270)
		return im
	def thumbnail(self, size=200):
		if self.cached_thumbnail:
			im = Image.open(self.cached_thumbnail)
			return im
		im = self.image()
		bbox = im.getbbox()
		w = bbox[2]
		h = bbox[3]
		if h > w:
			ret = im.crop((0, 0, w, w))
		else:
			x = int((w - h) / 2)
			ret = im.crop((x, 0, x + h, h))
		ret = ret.resize((size, size), 1)
		blob = BytesIO()
		ret.save(blob, 'JPEG')
		self.cached_thumbnail.save(photo_thumbnail_upload_location, File(blob), save=False)
		self.save(update_fields=['cached_thumbnail'])
		return ret
	def events(self):
		if self.time is None:
			return Event.objects.none()
		return Event.objects.filter(start_time__lte=self.time, end_time__gte=self.time)
	def generate_caption(self):
		if self.caption != '':
			return self.caption
		loc = ''
		ppl = ''
		if self.location:
			loc = str(self.location)
		else:
			if not((self.lat is None) or (self.lon is None)):
				loc = get_location_name(self.lat, self.lon)
		if self.people.count() > 0:
			ppla = []
			for p in self.people.all():
				ppla.append(str(p))
			if len(ppla) > 1:
				ppla[-1] = "and " + ppla[-1]
			if len(ppla) == 2:
				ppl = ' '.join(ppla)
			else:
				ppl = ', '.join(ppla)
		if loc == '':
			if ppl == '':
				return ''
			else:
				return "Photo of " + ppl
		else:
			if ppl == '':
				return "Photo taken at " + loc
			else:
				return "Photo of " + ppl + ", taken at " + loc
	def __str__(self):
		return 'Photo ' + str(self.file.path)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'photo'
		verbose_name_plural = 'photos'

class PersonPhoto(models.Model):
	person = models.ForeignKey(Person, on_delete=models.CASCADE)
	photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="photos")
	def __str__(self):
		return str(self.person) + ' in ' + str(self.photo)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'person photo'
		verbose_name_plural = 'person photos'

class Event(models.Model):
	"""A class representing an event in the life of the user. This is very vague and can mean
	pretty much anything. The intention is for people using Imouto as a health tracker would
	use events for exercise periods, people doing general lifelogging would use them for journeys
	or visits to places. They could also just be imported calendar appointments. You do you.
	"""
	start_time = models.DateTimeField()
	"""The start time of the Event, a datetime."""
	end_time = models.DateTimeField()
	"""The end time of the Event, a datetime."""
	created_time = models.DateTimeField(auto_now_add=True)
	"""A datetime representing the time this Event object was created."""
	updated_time = models.DateTimeField(auto_now=True)
	"""A datetime representing the time this Event object was last modified."""
	type = models.SlugField(max_length=32)
	"""The type of this Event. This is a string and can be anything you like, although certain values (eg journey, loc_prox, life_event) are treated differently by the UI."""
	caption = models.CharField(max_length=255, default='', blank=True)
	"""A human-readable caption for the Event, could also be described as the title or summary."""
	description = models.TextField(default='', blank=True)
	"""A human-readable description of the Event. This can be anything, but should provide some narrative or additional information to remembering what happened during this Event."""
	people = models.ManyToManyField(Person, through='PersonEvent')
	"""A many-to-many field of Person objects. It stores the people encountered during this Event."""
	location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
	"""The Location in which this Event took place."""
	geo = models.TextField(default='', blank=True)
	cached_health = models.TextField(default='', blank=True)
	cached_staticmap = models.ImageField(blank=True, null=True, upload_to=event_staticmap_upload_location)
	elevation = models.TextField(default='', blank=True)
	speed = models.TextField(default='', blank=True)
	cover_photo = models.ForeignKey(Photo, null=True,  blank=True, on_delete=models.SET_NULL)
	"""The Photo object that best illustrates this Event."""
	@property
	def show_hearttab(self):
		health = self.health()
		if 'heartavg' in health:
			return True
		if 'heartmax' in health:
			return True
		if 'heartavgprc' in health:
			return True
		if 'heartmaxprc' in health:
			return True
		if 'heartoptimaltime' in health:
			return True
		return False
	@property
	def show_elevationtab(self):
		health = self.health()
		if 'elevgain' in health:
			return True
		if 'elevloss' in health:
			return True
		if 'elevmin' in health:
			return True
		if 'elevmax' in health:
			return True
		return False
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		ret = {'id': self.pk, 'caption': self.caption, 'start_time': self.start_time.strftime("%Y-%m-%d %H:%M:%S %z"), 'end_time': self.end_time.strftime("%Y-%m-%d %H:%M:%S %z"), 'people': [], 'photos': [], 'geo': {}}
		if self.geo:
			ret['geo'] = self.geo
		else:
			if self.type == 'journey':
				self.__refresh_geo()
				if self.geo:
					ret['geo'] = self.geo
		if self.description:
			if self.description != '':
				ret['description'] = self.description
		if self.location:
			ret['place'] = self.location.to_dict()
		for person in self.people.all():
			ret['people'].append(person.to_dict())
		for photo in Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time):
			photo_path = str(photo.file.path)
			if os.path.exists(photo_path):
				ret['photos'].append(photo_path)
		if self.cached_health:
			health = self.health()
			if 'heart' in health:
				health['heart'] = json.loads(health['heart'])
			ret['health'] = health
		if self.type == 'life_event':
			events = []
			for event in self.subevents():
				events.append(event.to_dict())
			if len(events) > 0:
				ret['events'] = events
		if self.type == 'journey':
			if self.geo:
				ret['geometry'] = json.loads(self.geo)
		return ret
	def staticmap(self):
		if self.cached_staticmap:
			im = Image.open(self.cached_staticmap.path)
			return im
		if self.geo:
			geo = json.loads(self.geo)['geometry']
		else:
			geo = {'type': 'None'}
		if geo['type'] != 'MultiLineString':
			im = Image.new('RGB', (1024, 1024))
			blob = BytesIO()
			im.save(blob, format='png')
			return blob.getvalue()
		m = StaticMap(1024, 1024, url_template=settings.MAP_TILES)
		for polyline in geo['coordinates']:
			c = len(polyline)
			for i in range(1, c):
				coordinates = [polyline[i - 1], polyline[i]]
				line_shadow = Line(coordinates, '#FFFFFF', 10)
				m.add_line(line_shadow)
			for i in range(1, c):
				coordinates = [polyline[i - 1], polyline[i]]
				line = Line(coordinates, '#0000FF', 7)
				m.add_line(line)
		im = m.render()
		blob = BytesIO()
		im.save(blob, 'PNG')
		self.cached_staticmap.save(event_staticmap_upload_location, File(blob), save=False)
		self.save(update_fields=['cached_staticmap'])
		return im
	def tag(self, tagname):
		tagid = tagname.lower()
		try:
			tag = EventTag.objects.get(id=tagid)
		except:
			tag = EventTag(id=tagid, colour=('#' + str("%06x" % random.randint(0, 0xFFFFFF)).upper()))
			tag.save()
		self.tags.add(tag)
	def tags_field(self):
		ret = []
		for tag in self.tags.all():
			ret.append(tag.id)
		return ', '.join(ret)
	def description_html(self):
		if self.description == '':
			return ''
		md = markdown.Markdown()
		return md.convert(self.description)
	def refresh(self, save=True):
		if self.type == 'journey':
			geo = self.__refresh_geo(save=False)
			self.elevation = getelevation(self.start_time, self.end_time)
			self.speed = getspeed(self.start_time, self.end_time)
		if self.type == 'loc_prox':
			self.geo = ''
			self.elevation = ''
			self.speed = ''
		if len(self.cached_health) <= 2:
			health = self.__refresh_health(save=False)
		if save:
			self.save()
		if self.id:
			self.auto_tag()
			self.populate_people_from_photos()
	def subevents(self):
		return Event.objects.filter(start_time__gte=self.start_time, end_time__lte=self.end_time).exclude(id=self.id).order_by('start_time')
	def weather(self):
		if self.location is None:
			return None
		if self.location.weather_location is None:
			return None
		return self.location.weather_location.readings.filter(time__gte=self.start_time, time__lte=self.end_time).order_by('time')
	def commits(self):
		"""
		Every Git commit made during this event.
		"""
		return GitCommit.objects.filter(commit_date__gte=self.start_time, commit_date__lte=self.end_time).order_by('commit_date')
	def tasks_completed(self):
		"""
		All tasks that were marked as 'completed' during this event.
		"""
		return CalendarTask.objects.filter(time_completed__gte=self.start_time, time_completed__lte=self.end_time).order_by('time_completed')
	def __refresh_geo(self, save=True):
		try:
			ret = json.loads(getgeoline(self.start_time, self.end_time))
		except:
			ret = {}
		if 'geometry' in ret:
			if 'geometries' in ret['geometry']:
				try:
					max_hr = DataReading.objects.filter(end_time__gte=self.start_time, start_time__lte=self.end_time, type='heart-rate').order_by('-value')[0]
				except:
					max_hr = None
				if not(max_hr is None):
					opt_rate = int(float(max_heart_rate(max_hr.start_time)) / 2)
					if max_hr.value >= opt_rate:
						ds = max_hr.start_time.strftime("%Y-%m-%dT%H:%M:%S%z")
						lat, lon = get_logged_position(max_hr.start_time)
						if not(lat is None):
							ret['geometry']['geometries'].append({"type": "Point", "coordinates": [lon, lat], "properties": {"type": "poi", "time": ds, "label": "Highest heart rate " + str(max_hr.value) + "bpm at " + max_hr.start_time.strftime("%H:%M:%S")}})
		self.geo = json.dumps(ret)
		if save:
			self.save(update_fields=['geo'])
		return self.geo
	def gpx(self):
		dt = self.start_time
		root = minidom.Document()
		xml = root.createElement('gpx')
		xml.setAttribute('version', '1.1')
		xml.setAttribute('creator', 'Imouto')
		xml.setAttribute('xmlns', 'http://www.topografix.com/GPX/1/1')
		xml.setAttribute('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
		xml.setAttribute('xsi:schemaLocation', 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd')
		root.appendChild(xml)
		if self.geo:
			g = json.loads(self.geo)
			geom = []
			if 'geometry' in g:
				if 'coordinates' in g['geometry']:
					geom.append(g['geometry']['coordinates'])
				if 'geometries' in g['geometry']:
					for gg in g['geometry']['geometries']:
						if 'coordinates' in gg:
							geom.append(gg['coordinates'])
			for g in geom:
				trk = root.createElement('trk')
				for ptl in g:
					seg = root.createElement('trkseg')
					if not(isinstance(ptl, list)):
						continue
					for pt in ptl:
						ptx = root.createElement('trkpt')
						ptx.setAttribute('lat', str(pt[1]))
						ptx.setAttribute('lon', str(pt[0]))
						pdt = root.createElement('time')
						pdt.appendChild(root.createTextNode(dt.strftime("%Y-%m-%d %H:%M:%S").replace(' ', 'T') + 'Z'))
						dt = dt + datetime.timedelta(seconds=1)
						ptx.appendChild(pdt)
						seg.appendChild(ptx)
					trk.appendChild(seg)
				xml.appendChild(trk)
		return(root.toprettyxml(indent='\t'))
	def coordinates(self):
		dt = self.start_time
		ret = []
		if self.geo:
			g = json.loads(self.geo)
			if 'geometry' in g:
				if 'coordinates' in g['geometry']:
					for ptl in g['geometry']['coordinates']:
						for pt in ptl:
							item = [pt[1], pt[0]]
							ret.append(item)
		return(ret)

	def distance(self):
		if not(self.geo):
			return 0
		geo = json.loads(self.geo)
		if 'properties' in geo:
			if 'distance' in geo['properties']:
				return (float(int((geo['properties']['distance'] / 1.609) * 100)) / 100)
		return 0
	@property
	def length(self):
		return((self.end_time - self.start_time).total_seconds())
	@property
	def days(self):
		ds = self.start_time.date()
		de = self.end_time.date()
		dt = ds
		while dt<=de:
			create_or_get_day(dt)
			dt = dt + datetime.timedelta(days=1)
		return Day.objects.filter(date__gte=ds, date__lte=de).order_by('date')
	@property
	def timezone(self):
		days = self.days
		if days.count() == 0:
			return pytz.timezone(settings.TIME_ZONE)
		if days.count() == 1:
			return days[0].timezone
		ret = days[0].timezone
		for d in days:
			if d.timezone==ret:
				continue
			return pytz.timezone(settings.TIME_ZONE)
		return ret

	def length_string(self, value=0):
		s = value
		if s == 0:
			s = int((self.end_time - self.start_time).total_seconds())
		m = int(s / 60)
		s = s - (m * 60)
		h = int(m / 60)
		m = m - (h * 60)
		if((m == 0) & (h == 0)):
			return str(s) + ' seconds '
		if h == 0:
			if((m < 10) & (s > 0)):
				return str(m) + ' min, ' + str(s) + ' sec'
			else:
				return str(m) + ' minutes'
		if h > 36:
			d = int(h / 24)
			h = h - (d * 24)
			if((d == 1) & (h == 1)):
				return '1 day, 1 hour'
			if d == 1:
				return '1 day, ' + str(h) + ' hours'
			if h == 1:
				return str(d) + ' days, 1 hour'
			return str(d) + ' days, ' + str(h) + ' hours'
		if m > 0:
			return str(h) + ' hour, ' + str(m) + ' min'
		else:
			return str(h) + ' hour'
	def photos(self):
		ret = Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time)
		return ret.annotate(num_people=Count('people')).order_by('-num_people')
	def documents(self):
		return([])
	def messages(self, type=''):
		if type == '':
			return RemoteInteraction.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time).order_by('time')
		else:
			return RemoteInteraction.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time).filter(type=type).order_by('time')
	def sms(self):
		messages = self.messages('sms')
		people = []
		for message in messages:
			address = message.address.replace(' ', '')
			if address in people:
				continue
			people.append(address)
		ret = []
		for person in people:
			conversation = []
			for message in messages:
				address = message.address.replace(' ', '')
				if address == person:
					if len(conversation) > 0:
						delay = message.time - conversation[-1].time
						if delay.total_seconds() > (3 * 3600):
							ret.append(conversation)
							conversation = []
					conversation.append(message)
			if len(conversation) > 0:
				ret.append(conversation)
		return sorted(ret, key=lambda item: item[0].time)
	def health(self):
		if len(self.cached_health) > 2:
			return json.loads(self.cached_health)
		return self.__refresh_health()
	def __refresh_health(self, save=True):
		if len(self.cached_health) > 2:
			return json.loads(self.cached_health)
		max_hr = float(max_heart_rate(self.start_time))
		ret = {}
		heart_total = 0.0
		heart_count = 0.0
		heart_max = 0.0
		heart_threshold = int(max_hr * 0.5)
		heart_threshold_2 = int(max_hr * 0.7)
		heart_csv = []
		heart_json = []
		heart_zone = 0.0
		heart_zone_2 = 0.0
		cadence_csv = []
		cadence_json = []
		cadence_max = 0.0
		cadence_total = 0.0
		cadence_count = 0.0
		speed_count = 0
		speed_move_count = 0
		speed_move_time = 0.0
		speed_total = 0.0
		speed_max = 0.0
		step_count = 0
		elev_gain = 0.0
		elev_loss = 0.0
		elev_max = -99999.99
		elev_min = 99999.99
		sleep = []
		if self.length > 86400:
			eventsearch = DataReading.objects.filter(end_time__gte=self.start_time, start_time__lte=self.end_time).exclude(type='heart-rate').exclude(type='cadence').order_by('start_time')
		else:
			eventsearch = DataReading.objects.filter(end_time__gte=self.start_time, start_time__lte=self.end_time).order_by('start_time')
		cum = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
		for item in eventsearch:
			if item.start_time <= cum:
				continue
			cum = item.start_time
			if item.type=='cadence':
				cadence_csv.append(str(item.value))
				cadence_json.append({"x": item.start_time.strftime("%Y-%m-%d %H:%M:%S"), "y": item.value})
				cadence_total = cadence_total + float(item.value)
				cadence_count = cadence_count + 1.0
				if item.value > cadence_max:
					cadence_max = item.value
			if item.type=='heart-rate':
				heart_csv.append(str(item.value))
				heart_json.append({"x": item.start_time.strftime("%Y-%m-%d %H:%M:%S"), "y": item.value})
				heart_total = heart_total + float(item.value)
				heart_count = heart_count + 1.0
				if item.value > heart_max:
					heart_max = item.value
				if item.value > heart_threshold:
					zone_secs = (item.end_time - item.start_time).total_seconds()
					if item.value > heart_threshold_2:
						heart_zone_2 = heart_zone_2 + zone_secs
					else:
						heart_zone = heart_zone + zone_secs
			if item.type=='step-count':
				step_count = step_count + item.value
			if (item.type=='sleep') & (item.value <= 2):
				sleep.append(item)
		if self.speed != '':
			speed = json.loads(self.speed)
			first_entry = speed[0]
			last_time = datetime.datetime.strptime(re.sub('\.[0-9]+', '', first_entry['x']), "%Y-%m-%dT%H:%M:%S%z")
			for item in speed:
				cur_time = datetime.datetime.strptime(re.sub('\.[0-9]+', '', item['x']), "%Y-%m-%dT%H:%M:%S%z")
				time_diff = (cur_time - last_time).total_seconds()
				if item['y'] > speed_max:
					speed_max = item['y']
				speed_count = speed_count + 1
				speed_total = speed_total + item['y']
				if item['y'] > 1:
					speed_move_count = speed_move_count + 1
					speed_move_time = speed_move_time + time_diff
				last_time = cur_time
		if self.elevation != '':
			elev = json.loads(self.elevation)
			last_elev = elev[0]['y']
			for item in elev:
				e = item['y'] - last_elev
				if e > 0:
					elev_gain = elev_gain + e
				else:
					elev_loss = elev_loss + (0 - e)
				last_elev = item['y']
				if last_elev > elev_max:
					elev_max = last_elev
				if last_elev < elev_min:
					elev_min = last_elev
		if cadence_count > 0:
			ret['cadenceavg'] = int(cadence_total / cadence_count)
			ret['cadencemax'] = int(cadence_max)
			ret['cadence'] = json.dumps(cadence_json)
		if heart_count > 0:
			ret['heartavg'] = int(heart_total / heart_count)
			ret['heartmax'] = int(heart_max)
			ret['heartavgprc'] = int(((heart_total / heart_count) / max_hr) * 100)
			ret['heartmaxprc'] = int((heart_max / max_hr) * 100)
			ret['heartzonetime'] = [int(self.length - (heart_zone + heart_zone_2)), int(heart_zone), int(heart_zone_2)]
			ret['heartoptimaltime'] = self.length_string(ret['heartzonetime'][1])
			ret['efficiency'] = int((float(ret['heartzonetime'][1]) / float(ret['heartzonetime'][0] + ret['heartzonetime'][1] + ret['heartzonetime'][2])) * 100.0)
			ret['heart'] = ','.join(heart_csv)
			ret['heart'] = json.dumps(heart_json)
		if ((elev_gain > 0) & (elev_loss > 0)):
			ret['elevgain'] = int(elev_gain)
			ret['elevloss'] = int(elev_loss)
		if elev_min < 99999.99:
			ret['elevmin'] = int(elev_min)
		if elev_max > -99999.99:
			ret['elevmax'] = int(elev_max)
		if len(sleep) > 0:
			ret['sleep'] = parse_sleep(sleep, self.timezone)
		if step_count > 0:
			ret['steps'] = step_count
		if speed_count > 0:
			ret['speedavg'] = int(speed_total / speed_count)
			ret['speedavgmoving'] = int(speed_total / speed_move_count)
			ret['speedmax'] = int(speed_max)
			ret['speedmoving'] = self.length_string(int(speed_move_time))
		self.cached_health = json.dumps(ret)
		if save:
			self.save(update_fields=['cached_health'])
		return ret
	def populate_people_from_photos(self):
		for photo in self.photos():
			if photo.people.count() == 0:
				continue
			for person in photo.people.all():
				if person in self.people.all():
					continue
				self.people.add(person)
	def auto_tag(self):
		for tag in AutoTag.objects.all():
			if tag.eval(self):
				self.tag(str(tag.tag))
		if self.type == 'life_event':
			for e in self.subevents():
				for tag in e.tags.all():
					self.tags.add(tag)

	@property
	def similar(self):
		return list(self.similar_to.filter(diff_value__lt=0.1).order_by('diff_value').values('event1', 'event1__caption', 'event1__start_time', 'diff_value'))
	def __str__(self):
		if self.caption == '':
			return "Event " + str(self.pk)
		else:
			return self.caption
	class Meta:
		app_label = 'viewer'
		verbose_name = 'event'
		verbose_name_plural = 'events'
		indexes = [
			models.Index(fields=['start_time']),
			models.Index(fields=['end_time']),
			models.Index(fields=['type'])
		]

class LifePeriod(models.Model):
	"""A LifePeriod is a period longer than an Event. It may be used for things such as
	living in a particular town, attending a particular school or working in a particular
	job."""
	start_time = models.DateField()
	"""The start time of the LifePeriod, a date object."""
	end_time = models.DateField()
	"""The end time of the LifePeriod, a date object."""
	created_time = models.DateTimeField(auto_now_add=True)
	"""A datetime representing the time this LifePeriod object was created."""
	updated_time = models.DateTimeField(auto_now=True)
	"""A datetime representing the time this LifePeriod object was last modified."""
	caption = models.CharField(max_length=255, default='', blank=True)
	"""A human-readable caption for the LifePeriod, could also be described as the title or summary."""
	description = models.TextField(default='', blank=True)
	"""A human-readable description of the LifePeriod. This can be anything, but should provide some narrative or additional information to remembering what happened during this LifePeriod."""
	cover_photo = models.ForeignKey(Photo, null=True,  blank=True, on_delete=models.SET_NULL)
	"""The Photo object that best illustrates this LifePeriod."""
	colour = ColorField(default='#777777')
	"""The colour in which this LifePeriod will be drawn on the life grid view"""
	type = models.SlugField(max_length=32)
	"""The type or category of this LifePeriod. This is a string and can be anything you like"""
	def __str__(self):
		return(self.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life period'
		verbose_name_plural = 'life periods'

class PersonEvent(models.Model):
	person = models.ForeignKey(Person, on_delete=models.CASCADE)
	event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="events")
	def __str__(self):
		return str(self.person) + ' in ' + str(self.event)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'person event'
		verbose_name_plural = 'person events'

class LifeReport(models.Model):
	"""This class represents a yearly life report, inspired by the work of Nicholas Felton.
	It is intended to be created semi-automatically; statistical information created
	through data analysis before being augmented with specific information that only a
	human can add, for example, favourite movie of the year. Once the report has been
	created, a background process may be used to generate a PDF file.
	"""
	label = models.CharField(max_length=128)
	year = models.IntegerField()
	style = models.SlugField(max_length=32, default='default')
	people = models.ManyToManyField(Person, through='ReportPeople')
	locations = models.ManyToManyField(Location, through='ReportLocations')
	events = models.ManyToManyField(Event, through='ReportEvents')
	created_date = models.DateTimeField(auto_now_add=True)
	modified_date = models.DateTimeField(auto_now=True)
	pdf = models.FileField(blank=True, null=True, upload_to=report_pdf_upload_location)
	cached_wordcloud = models.ImageField(blank=True, null=True, upload_to=report_wordcloud_upload_location)
	cached_dict = models.TextField(blank=True, null=True)
	options = models.TextField(default='{}')
	def __format_date(self, dt):
		return dt.strftime("%a %-d %b") + ' ' + (dt.strftime("%I:%M%p").lower().lstrip('0'))
	def categories(self):
		ret = []
		for prop in LifeReportProperties.objects.filter(report=self):
			propkey = str(prop.category)
			if propkey == '':
				propkey = 'misc'
			if propkey in ret:
				continue
			ret.append(propkey)
		for graph in LifeReportGraph.objects.filter(report=self):
			propkey = str(graph.category)
			if propkey == '':
				propkey = 'misc'
			if propkey in ret:
				continue
			ret.append(propkey)
		for chart in LifeReportChart.objects.filter(report=self):
			propkey = str(chart.category)
			if propkey == '':
				propkey = 'misc'
			if propkey in ret:
				continue
			ret.append(propkey)
		if not('misc' in ret):
			ret.append('misc')
		return ret
	def countries(self):
		return LocationCountry.objects.filter(locations__in=self.locations.all()).distinct()
	def refresh_events(self):
		tz = pytz.timezone(settings.TIME_ZONE)
		dts = tz.localize(datetime.datetime(self.year, 1, 1, 0, 0, 0))
		dte = tz.localize(datetime.datetime(self.year, 12, 31, 23, 59, 59))
		subevents = []
		self.events.clear()
		self.cached_dict = None
		self.save(update_fields=['cached_dict'])
		for event in Event.objects.filter(type='life_event', start_time__lte=dte, end_time__gte=dts).order_by('start_time'):
			self.events.add(event)
			if event.location:
				self.locations.add(event.location)
			for e in event.subevents():
				if e in subevents:
					continue
				subevents.append(e)
		for event in Event.objects.filter(start_time__lte=dte, end_time__gte=dts).order_by('start_time').exclude(type='life_event'):
			if event.location:
				self.locations.add(event.location)
			if event in subevents:
				continue
			if event.photos().count() > 5:
				self.events.add(event)
				continue
			if event.description is None:
				continue
			if event.description == '':
				continue
			self.events.add(event)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		if self.cached_dict:
			return json.loads(self.cached_dict)
		ret = {'id': self.pk, 'label': self.label, 'year': self.year, 'stats': [], 'created_date': self.created_date.strftime("%Y-%m-%d %H:%M:%S %z"), 'modified_date': self.modified_date.strftime("%Y-%m-%d %H:%M:%S %z"), 'style': self.style, 'type': 'year', 'people': [], 'places': [], 'countries': [], 'life_events': [], 'events': []}
		for personlink in ReportPeople.objects.filter(report=self):
			person = personlink.person
			persondata = person.to_dict()
			if personlink.first_encounter:
				persondata['first_encounter'] = personlink.first_encounter.strftime("%Y-%m-%d %H:%M:%S %z")
			persondata['encounter_days'] = json.loads(personlink.day_list)
			ret['people'].append(persondata)
		for place in self.locations.all():
			ret['places'].append(place.to_dict())
		for event in self.events.filter(type='life_event').order_by('start_time'):
			ret['life_events'].append(event.to_dict())
		for event in self.events.exclude(type='life_event').order_by('start_time'):
			ret['events'].append(event.to_dict())
		for prop in LifeReportProperties.objects.filter(report=self).order_by('category'):
			ret['stats'].append(prop.to_dict())
		for country in self.countries():
			ret['countries'].append(country.to_dict())
		self.cached_dict = json.dumps(ret)
		self.save(update_fields=['cached_dict'])
		return ret
	def pages(self):
		ret = []
		done = []
		photos_done = []
		options = json.loads(self.options)
		if not('reportdetail' in options):
			options['reportdetail'] = 'minimal'
		if not('peoplestats' in options):
			options['peoplestats'] = False
		if not('wordcloud' in options):
			options['wordcloud'] = False
		if not('maps' in options):
			options['maps'] = False
		year = self.year
		months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		title = str(year)
		subtitle = str(self.label)
		if title == subtitle:
			subtitle = ''
		ret.append({'type': 'title', 'image': None, 'title': title, 'subtitle': subtitle})
		if options['wordcloud'] == True:
			if self.cached_wordcloud:
				ret.append({'type': 'image', 'image': self.cached_wordcloud.path})
		if options['maps'] == False:
			checked = []
			for event in self.events.filter(type='life_event'):
				for subevent in event.subevents():
					checked.append(subevent.id)
					if ((subevent.photos().count() < 5) & (subevent.description == '')):
						done.append(subevent.id)
					if ((subevent.photos().count() < 5) & (subevent.description is None)):
						done.append(subevent.id)
			for event in self.events.exclude(type='life_event'):
				if event.id in checked:
					continue
				if ((event.photos().count() == 0) & (event.description == '')):
					done.append(subevent.id)
		for category in list(LifeReportProperties.objects.filter(report=self).values_list('category', flat=True).distinct()):
			item = {'type': 'stats', 'title': category, 'data': []}
			for prop in LifeReportProperties.objects.filter(report=self, category=category):
				item['data'].append(prop.to_dict())
			if len(item['data']) > 0:
				ret.append(item)
			item = {'type': 'grid', 'title': category, 'data': []}
			for graph in LifeReportGraph.objects.filter(report=self, category=category):
				item['data'].append(graph.to_dict())
			if len(item['data']) > 0:
				ret.append(item)
		for chart in LifeReportChart.objects.filter(report=self):
			if options['peoplestats'] == False:
				if chart.text.lower() == 'people':
					continue
			item = {'type': 'chart', 'title': chart.text}
			if chart.description:
				if len(chart.description) > 0:
					item['description'] = chart.description
			item['data'] = json.loads(chart.data)
			ret.append(item)

		if options['peoplestats'] == True:
			item = {'type': 'chart', 'title': "People", 'description': "Top 10 people encountered, ranked by the number of times met over the course of the year."}
			item_data = []
			for pl in ReportPeople.objects.filter(report=self):
				value = {"text": pl.person.full_name(), "value": len(json.loads(pl.day_list))}
				if pl.person.image:
					value['image'] = pl.person.image.path
				item_data.append(value)
			item['data'] = sorted(item_data, reverse=True, key=lambda d: d['value'])
			item['data'] = item['data'][0:10]
			ret.append(item)

		if options['reportdetail'] == 'standard':
			page_count = len(ret)
			for event in self.events.filter(type='life_event').order_by('start_time'):
				if event.id in done:
					continue
				done.append(event.id)
				item = {'type': 'feature', 'title': event.caption, 'description': event.description}
				if event.cover_photo:
					item['image'] = event.cover_photo.id
				ret.append(item)
				for pc in event.photo_collages.all():
					new_photos = False
					for photo in pc.photos.all():
						if photo.id in photos_done:
							continue
						photos_done.append(photo.id)
						new_photos = True
					if new_photos:
						if pc.image.size >= 1000:
							ret.append({'type': 'image', 'text': event.caption, 'image': pc.image.path})
				subevents = []
				collages = []
				for subevent in event.subevents().order_by('start_time'):
					if subevent.id in done:
						continue
					done.append(subevent.id)
					for pc in subevent.photo_collages.all():
						new_photos = False
						for photo in pc.photos.all():
							if photo.id in photos_done:
								continue
							photos_done.append(photo.id)
							new_photos = True
						if new_photos:
							if pc.image.size >= 1000:
								collages.append([pc.event.caption, pc.image.path])
					if ((subevent.description) or (subevent.cover_photo) or (subevent.cached_staticmap)):
						item = {'title': subevent.caption, 'description': subevent.description, 'date': self.__format_date(subevent.start_time)}
						if subevent.cover_photo:
							item['image'] = subevent.cover_photo.id
						elif subevent.cached_staticmap:
							if options['maps'] == True:
								item['image'] = subevent.cached_staticmap.path
						if len(subevent.description) < 1000:
							subevents.append(item)
						else:
							ret.append({'type': 'items', 'data': [item]})
					if len(subevents) >= 3:
						ret.append({'type': 'items', 'data': subevents})
						subevents = []
						for pc in collages:
							ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})
						collages = []
				if len(subevents) > 0:
					ret.append({'type': 'items', 'data': subevents})
				for pc in collages:
					ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})

		if options['reportdetail'] == 'full':
			for i in range(0, 12):
				ret.append({'type': 'title', 'image': None, 'title': months[i]})
				page_count = len(ret)
				dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year, (i + 1), 1, 0, 0, 0))
				if i < 11:
					dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year, (i + 2), 1, 0, 0, 0)) - datetime.timedelta(seconds=1)
				else:
					dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime((year + 1), 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)
				people = []
				for person in Person.objects.filter(reports__report=self, reports__first_encounter__gte=dts, reports__first_encounter__lte=dte):
					item = {'name': person.full_name()}
					if person.image:
						item['image'] = person.image.path
					if not('image' in item):
						continue # For now, just don't show anyone with no photo
					people.append(item)
				if len(people) > 0:
					grid_max = len(people)
					while grid_max > 16:
						grid_max = int((float(grid_max) / 2) + 0.5)
					while len(people) > 0:
						if options['peoplestats'] == True:
							ret.append({'type': 'grid', 'title': 'People', 'data': people[0:grid_max]})
						people = people[grid_max:]
				events = self.events.filter(end_time__gte=dts, start_time__lte=dte)
				for event in events.filter(type='life_event').order_by('start_time'):
					if event.id in done:
						continue
					done.append(event.id)
					item = {'type': 'feature', 'title': event.caption, 'description': event.description}
					if event.cover_photo:
						item['image'] = event.cover_photo.id
					ret.append(item)
					for pc in event.photo_collages.all():
						new_photos = False
						for photo in pc.photos.all():
							if photo.id in photos_done:
								continue
							photos_done.append(photo.id)
							new_photos = True
						if new_photos:
							if pc.image.size >= 1000:
								ret.append({'type': 'image', 'text': event.caption, 'image': pc.image.path})
					subevents = []
					collages = []
					for subevent in event.subevents().order_by('start_time'):
						if subevent.id in done:
							continue
						done.append(subevent.id)
						for pc in subevent.photo_collages.all():
							new_photos = False
							for photo in pc.photos.all():
								if photo.id in photos_done:
									continue
								photos_done.append(photo.id)
								new_photos = True
							if new_photos:
								if pc.image.size >= 1000:
									collages.append([pc.event.caption, pc.image.path])
						if ((subevent.description) or (subevent.cover_photo) or (subevent.cached_staticmap)):
							item = {'title': subevent.caption, 'description': subevent.description, 'date': self.__format_date(subevent.start_time)}
							if subevent.cover_photo:
								item['image'] = subevent.cover_photo.id
							elif subevent.cached_staticmap:
								if options['maps'] == True:
									item['image'] = subevent.cached_staticmap.path
							if len(subevent.description) < 1000:
								subevents.append(item)
							else:
								ret.append({'type': 'items', 'data': [item]})
						if len(subevents) >= 3:
							ret.append({'type': 'items', 'data': subevents})
							subevents = []
							for pc in collages:
								ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})
							collages = []
					if len(subevents) > 0:
						ret.append({'type': 'items', 'data': subevents})
					for pc in collages:
						ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})
				subevents = []
				collages = []
				for subevent in events.exclude(type='life_event').order_by('start_time'):
					if subevent.id in done:
						continue
					done.append(subevent.id)
					for pc in subevent.photo_collages.all():
						new_photos = False
						for photo in pc.photos.all():
							if photo.id in photos_done:
								continue
							photos_done.append(photo.id)
							new_photos = True
						if new_photos:
							if pc.image.size >= 1000:
								collages.append([pc.event.caption, pc.image.path])
					if ((subevent.description) or (subevent.cover_photo) or (subevent.cached_staticmap)):
						item = {'title': subevent.caption, 'description': subevent.description, 'date': self.__format_date(subevent.start_time)}
						if subevent.cover_photo:
							item['image'] = subevent.cover_photo.id
						elif subevent.cached_staticmap:
							if options['maps'] == True:
								item['image'] = subevent.cached_staticmap.path
						if len(subevent.description) < 1000:
							subevents.append(item)
						else:
							ret.append({'type': 'items', 'data': [item]})
					if len(subevents) >= 3:
						ret.append({'type': 'items', 'data': subevents})
						subevents = []
						for pc in collages:
							ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})
						collages = []
				if len(subevents) > 0:
					ret.append({'type': 'items', 'data': subevents})
				for pc in collages:
					ret.append({'type': 'image', 'text': pc[0], 'image': pc[1]})
				if len(ret) == page_count:
					# No new pages were added this month, we may as well get rid of the month title page
					if page_count >= 1:
						page_count = page_count - 1
						ret = ret[0:page_count]
		return ret
	def words(self):
		text = ''
		for event in self.events.all():
			text = text + event.description + ' '
			for msg in event.messages():
				if msg.incoming:
					continue
				if ((msg.type != 'sms') & (msg.type != 'microblogpost')):
					continue
				text = text + msg.message + ' '
		text = re.sub('=[0-9A-F][0-9A-F]', '', text)
		text = strip_tags(text)
		text = text.strip()
		ret = []
		for word in text.split(' '):
			if len(word) < 3:
				continue
			if word.startswith("I'"):
				continue
			if word.endswith("'s"):
				word = word[:-2]
			ret.append(word)
		return ' '.join(ret)
	def wordcloud(self):
		if self.cached_wordcloud:
			im = Image.open(self.cached_wordcloud.path)
			return im
		text = self.words()
		stopwords = set()
		for word in set(STOPWORDS):
			stopwords.add(word)
			stopwords.add(word.capitalize())
		wc = WordCloud(width=2598, height=3543, background_color=None, mode='RGBA', max_words=500, stopwords=stopwords, font_path=settings.DEFAULT_FONT).generate(text)
		im = wc.to_image()
		blob = BytesIO()
		im.save(blob, 'PNG')
		self.cached_wordcloud.save(report_wordcloud_upload_location, File(blob), save=False)
		self.save(update_fields=['cached_wordcloud'])
		return im
	def life_events(self):
		return self.events.filter(type='life_event')
	def diary_entries(self):
		return self.events.exclude(type='life_event').exclude(description='').order_by('start_time')
	def countries(self):
		ret = LocationCountry.objects.none()
		for data in self.locations.values('country').distinct():
			if not('country' in data):
				continue
			ret = ret | LocationCountry.objects.filter(a2=str(data['country']))
		return ret
	def addproperty(self, key, value, category=""):
		try:
			ret = LifeReportProperties.objects.get(key=key, category=str(category), report=self)
		except:
			ret = LifeReportProperties(key=key, value='', category=str(category), report=self)
		ret.value = str(value)
		ret.save()
		return ret
	def geo(self):
		features = []
		minlat = 360.0
		maxlat = -360.0
		minlon = 360.0
		maxlon = -360.0
		for location in self.locations.all():
			point = {}
			point['type'] = "Point"
			point['coordinates'] = [location.lon, location.lat]
			if location.lon > maxlon:
				maxlon = location.lon
			if location.lon < minlon:
				minlon = location.lon
			if location.lat > maxlat:
				maxlat = location.lat
			if location.lat < minlat:
				minlat = location.lat
			feature = {}
			properties = {}
			properties['label'] = str(location)
			if location.image:
				properties['image'] = 'places/' + location.uid + '_thumb.jpg'
			feature['type'] = 'Feature'
			feature['geometry'] = point
			feature['properties'] = properties
			features.append(feature)
		ret = {}
		ret['type'] = "FeatureCollection"
		ret['bbox'] = [minlon - 0.0025, minlat - 0.0025, maxlon + 0.0025, maxlat + 0.0025]
		ret['features'] = features
		return json.dumps(ret);
	def __str__(self):
		return self.label
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report'
		verbose_name_plural = 'life reports'

class ReportPeople(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
	person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="reports")
	first_encounter = models.DateTimeField(null=True)
	day_list = models.TextField(default='[]')
	comment = models.TextField(null=True, blank=True)
	def __str__(self):
		return str(self.person) + ' in ' + str(self.report)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'report person'
		verbose_name_plural = 'report people'

class ReportLocations(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
	location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="reports")
	comment = models.TextField(null=True, blank=True)
	def __str__(self):
		return str(self.location) + ' in ' + str(self.report)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'report location'
		verbose_name_plural = 'report locations'

class ReportEvents(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
	event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reports")
	comment = models.TextField(null=True, blank=True)
	def __str__(self):
		return str(self.event) + ' in ' + str(self.report)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'report event'
		verbose_name_plural = 'report events'

class Month(models.Model):
	month = models.IntegerField(validators=[MaxValueValidator(12), MinValueValidator(1)])
	year = models.IntegerField()
	@property
	def slug(self):
		"""
		The unique 'slug id' for this Month object, as would be displayed after the '#' in the URL bar.
		"""
		return("month_" + datetime.date(self.year, self.month, 1).strftime('%Y%m'))
	@property
	def this_month(self):
		"""
		Determines if this month represents the current month in real time.
		"""
		dt = datetime.datetime.now().date()
		if ((dt.month == self.month) & (dt.year == self.year)):
			return True
		return False
	@property
	def next(self):
		"""
		Returns the Day object representing the day after the one represented by this Day object.
		"""
		if self.this_month:
			return None
		y = self.year
		m = self.month
		m = m + 1
		if m > 12:
			m = m - 12
			y = y + 1
		return create_or_get_month(year=y, month=m)
	@property
	def previous(self):
		"""
		Returns the Day object representing the day before the one represented by this Day object.
		"""
		y = self.year
		m = self.month
		m = m - 1
		if m < 1:
			m = m + 12
			y = y - 1
		return create_or_get_month(year=y, month=m)
	@property
	def days(self):
		"""
		Every day in this month.
		"""
		dts = datetime.date(self.year, self.month, 1)
		if self.month < 12:
			dte = datetime.date(self.year, self.month + 1, 1)
		else:
			dte = datetime.date(self.year + 1, 1, 1)
		dt = dts
		while dt < dte:
			create_or_get_day(dt)
			dt = dt + datetime.timedelta(days=1)
		return Day.objects.filter(date__gte=dts, date__lt=dte).order_by('date')
	@property
	def earliest_morning(self):
		"""
		The day with the earliest wake_time in this month.
		"""
		dts = datetime.date(self.year, self.month, 1)
		if self.month < 12:
			dte = datetime.date(self.year, self.month + 1, 1)
		else:
			dte = datetime.date(self.year + 1, 1, 1)
		dt = dts
		ret = None
		early = 86400
		while dt < dte:
			day = create_or_get_day(dt)
			day_midnight = day.timezone.localize(datetime.datetime.combine(dt, datetime.datetime.min.time()))
			if day.wake_time is None:
				dt = dt + datetime.timedelta(days=1)
				continue
			before_wake = (day.wake_time - day_midnight).total_seconds()
			if before_wake < early:
				early = before_wake
				ret = day
			dt = dt + datetime.timedelta(days=1)
		return ret
	@property
	def latest_night(self):
		"""
		The day with the latest bed_time in this month.
		"""
		dts = datetime.date(self.year, self.month, 1)
		if self.month < 12:
			dte = datetime.date(self.year, self.month + 1, 1)
		else:
			dte = datetime.date(self.year + 1, 1, 1)
		dt = dts
		ret = None
		latest = 0
		while dt < dte:
			day = create_or_get_day(dt)
			day_midnight = day.timezone.localize(datetime.datetime.combine(dt, datetime.datetime.min.time()))
			if day.bed_time is None:
				dt = dt + datetime.timedelta(days=1)
				continue
			before_bed = (day.bed_time - day_midnight).total_seconds()
			if before_bed > latest:
				latest = before_bed
				ret = day
			dt = dt + datetime.timedelta(days=1)
		return ret
	@property
	def average_sunlight(self):
		"""
		Returns the month's average daily sunlight
		"""
		return self.days.annotate(total_sunlight=F('sunset_time')-F('sunrise_time')).aggregate(average_sunlight=Avg('total_sunlight'))['average_sunlight']
	@property
	def people(self):
		"""
		Every person encountered during this month.
		"""
		dtsd = datetime.date(self.year, self.month, 1)
		if self.month < 12:
			dted = datetime.date(self.year, self.month + 1, 1)
		else:
			dted = datetime.date(self.year + 1, 1, 1)
		try:
			dts = create_or_get_day(dtsd).wake_time
			dte = create_or_get_day(dted).bed_time
		except:
			return Person.objects.none()
		if dts is None:
			dts = pytz.utc.localize(datetime.datetime(dtsd.year, dtsd.month, 1, 0, 0, 0))
		if dte is None:
			dte = pytz.utc.localize(datetime.datetime(dted.year, dted.month, dted.day, 23, 59, 59))
		return Person.objects.filter(event__end_time__gt=dts, event__start_time__lt=dte).annotate(event_count=Count('event')).order_by('-event_count')
	@property
	def events(self):
		"""
		Every described event during this month.
		"""
		dts = pytz.utc.localize(datetime.datetime(self.year, self.month, 1, 0, 0, 0))
		if self.month < 12:
			dte = pytz.utc.localize(datetime.datetime(self.year, self.month + 1, 1, 0, 0, 0) - datetime.timedelta(seconds=1))
		else:
			dte = pytz.utc.localize(datetime.datetime(self.year + 1, 1, 1, 0, 0, 0) - datetime.timedelta(seconds=1))
		return Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by('start_time')
	@property
	def locations(self):
		"""
		Every location visited during this month.
		"""
		return Location.objects.filter(events__in=self.events).distinct()
	@property
	def life_events(self):
		"""
		Every described life event during this month.
		"""
		dts = datetime.datetime(self.year, self.month, 1, 0, 0, 0)
		if self.month < 12:
			dte = datetime.datetime(self.year, self.month + 1, 1, 0, 0, 0) - datetime.timedelta(seconds=1)
		else:
			dte = datetime.datetime(self.year + 1, 1, 1, 0, 0, 0) - datetime.timedelta(seconds=1)
		return Event.objects.filter(start_time__gte=dts, start_time__lte=dte, type="life_event").order_by('start_time')
	def workouts(self):
		ret = []
		for wc in EventWorkoutCategory.objects.all():
			item = [str(wc), 0.0]
			for event in self.events.filter(type='journey', workout_categories=wc):
				item[1] = item[1] + event.distance()
			if item[1] > 0.0:
				item[1] = float(int(item[1] * 100)) / 100
				ret.append(item)
		return ret
	def location_categories(self):
		categories = {}
		for loc in Location.objects.filter(events__in=self.events.filter(type='loc_prox').exclude(location__pk=settings.USER_HOME_LOCATION)).annotate(time_spent=F('events__end_time')-F('events__start_time')).annotate(total_time=Sum('time_spent')).order_by('-total_time'):
			for c in loc.categories.all():
				if not(c.pk in categories):
					categories[c.pk] = [c, 0]
				categories[c.pk][1] = categories[c.pk][1] + int(loc.total_time.total_seconds())
		return list(categories.values())
	def location_categories_chart(self):
		ret = [[], []]
		for item in self.location_categories():
			ret[0].append(str(item[0]))
			ret[1].append(item[1])
		return (json.dumps(ret[0]), json.dumps(ret[1]))
	def __str__(self):
		return(datetime.date(self.year, self.month, 1).strftime('%B %Y'))
	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['month', 'year'], name='month and year')
		]

class Day(models.Model):
	"""This class represents a day. This is necessary because a day may not begin
	and end at midnight. I personally often go to bed after midnight, and if you
	travel across timezones then a day may start at different times (UTC) to
	the times they start at home. This class is also a crafty way of caching
	certain health data.
	"""
	date = models.DateField(primary_key=True)
	wake_time = models.DateTimeField(null=True, blank=True)
	bed_time = models.DateTimeField(null=True, blank=True)
	timezone_str = models.CharField(max_length=32, default='UTC')
	cached_heart = models.TextField(null=True, blank=True)
	cached_sleep = models.TextField(null=True, blank=True)

	is_public_holiday = models.BooleanField(default=False)
	sunrise_time = models.DateTimeField(null=True, blank=True)
	sunset_time = models.DateTimeField(null=True, blank=True)

	def __dts__(self):
		"""
		Generates a fail-safe 'start time' for this day
		"""
		d = self.date
		if self.wake_time:
			return self.wake_time
		return self.timezone.localize(datetime.datetime(d.year, d.month, d.day, 4, 0, 0))
	def __dte__(self):
		"""
		Generates a fail-safe 'end time' for this day
		"""
		if not(self.today):
			if self.tomorrow.wake_time:
				return self.tomorrow.wake_time
		return self.__dts__() + datetime.timedelta(seconds=86400)

	def __calculate_wake_time(self):

		d = self.date
		dts = self.timezone.localize(datetime.datetime(d.year, d.month, d.day, 0, 0, 0))
		dte = dts + datetime.timedelta(seconds=86400)
		wakes = DataReading.objects.filter(type='awake', start_time__gte=dts, start_time__lt=dte).order_by('start_time')
		wakecount = wakes.count()
		if wakecount > 0:
			main_wake = None
			for wake in wakes:
				if main_wake is None:
					main_wake = wake
					continue
				if main_wake.length() < wake.length():
					main_wake = wake
			return main_wake.start_time.astimezone(self.timezone), main_wake.end_time.astimezone(self.timezone)
		else:
			dts = self.timezone.localize(datetime.datetime(d.year, d.month, d.day, 4, 0, 0))
			dte = dts + datetime.timedelta(seconds=86400)
			return dts, dte

	@property
	def today(self):
		"""
		Determines if this day represents today in real time.
		"""
		return (datetime.datetime.now().date() == self.date)
	@property
	def month(self):
		"""
		Returns the Month object that contains this Day.
		"""
		return create_or_get_month(self.date.month, self.date.year)
	@property
	def slug(self):
		"""
		The unique 'slug id' for this Day object, as would be displayed after the '#' in the URL bar.
		"""
		return("day_" + self.date.strftime('%Y%m%d'))
	@property
	def tomorrow(self):
		"""
		Returns the Day object representing the day after the one represented by this Day object.
		"""
		return create_or_get_day(self.date + datetime.timedelta(days=1))
	@property
	def yesterday(self):
		"""
		Returns the Day object representing the day before the one represented by this Day object.
		"""
		return create_or_get_day(self.date - datetime.timedelta(days=1))
	@property
	def length(self):
		"""
		Returns the length of the day (ie bedtime minus wake time).
		"""
		if ((self.bed_time is None) or (self.wake_time is None)):
			dts, dte = self.__calculate_wake_time()
		else:
			dts = self.wake_time
			dte = self.bed_time
		return (dte - dts)
	@property
	def timezone(self):
		"""
		Returns the relevant time zone for this particular day (ie it would normally be the same as settings.TIME_ZONE, but the user may be travelling abroad.)
		"""
		return pytz.timezone(self.timezone_str)
	@property
	def people(self):
		"""
		All the people encountered on this particular day.
		"""
		return Person.objects.filter(event__in=self.events).distinct()
	@property
	def events(self):
		"""
		Every described event on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return Event.objects.filter(end_time__gte=dts, end_time__lte=dte).exclude(type='life_event').order_by('start_time')
	@property
	def calendar(self):
		"""
		Every calendar appointment scheduled on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return CalendarAppointment.objects.filter(end_time__gte=dts, end_time__lte=dte).values('id', 'eventid', 'caption')
	@property
	def tweets(self):
		"""
		Every microblogpost (typically tweets, could be toots) made on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return RemoteInteraction.objects.filter(time__gte=dts, time__lte=dte, type='microblogpost', address='').order_by('time')
	@property
	def commits(self):
		"""
		Every Git commit made on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return GitCommit.objects.filter(commit_date__gte=dts, commit_date__lte=dte).order_by('commit_date')
	@property
	def tasks_completed(self):
		"""
		Every task marked as 'completed' on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return CalendarTask.objects.filter(time_completed__gte=dts, time_completed__lte=dte).order_by('time_completed')
	@property
	def sms(self):
		"""
		Every SMS message sent or received on this particular day.
		"""
		d = self.date
		dts = self.__dts__()
		dte = self.__dte__()
		return RemoteInteraction.objects.filter(time__gte=dts, time__lte=dte, type='sms').order_by('time')

	@property
	def max_heart_rate(self):
		"""
		The highest heart rate experienced on this particular day, according to the stored data. Returns 0 if no data is available.
		"""
		data = self.get_heart_information(False)
		if 'heart' in data:
			if 'day_max_rate' in data['heart']:
				return data['heart']['day_max_rate']
		return 0

	@property
	def optimal_heart_time(self):
		"""
		The time spent in the 'optimal' heart rate (ie between 50% and 70% of maximum) on this particular day, according to the stored data. Returns 0 if no data is available.
		"""
		data = self.get_heart_information(False)
		if 'heart' in data:
			if 'heartzonetime' in data['heart']:
				return data['heart']['heartzonetime'][1]
		return 0

	@property
	def steps(self):
		"""
		The number of steps taken during this particular day, according to the stored data.
		"""
		dts, dte = self.__calculate_wake_time()
		obj = DataReading.objects.filter(type='step-count').filter(start_time__gte=dts, end_time__lt=dte).aggregate(steps=Sum('value'))
		try:
			ret = int(obj['steps'])
		except:
			ret = 0
		return ret

	@property
	def average_mood(self):
		"""
		The average mood of the user during thie particular Day. Returns None if no mood data found.
		"""
		dts, dte = self.__calculate_wake_time()
		obj = DataReading.objects.filter(type='mood').filter(start_time__gte=dts, start_time__lte=dte).aggregate(mood=Avg('value'))
		try:
			ret = int(float(obj['mood']) + 0.5)
		except:
			ret = None
		return ret

	def data_readings(self, type):
		"""
		Returns all DataReading object of the type specified, logged on this particular day.

		:param type: The type of readings to return.
		:return: A QuerySet of DataReading objects.
		:rtype: QuerySet(DataReading)
		"""
		dts, dte = self.__calculate_wake_time()
		return DataReading.objects.filter(end_time__gte=dts, start_time__lte=dte, type=type)

	def get_heart_information(self, graph=True):
		"""
		Returns a summary of the stored heart rate data for the day in question.

		:param graph: True if you want the function to return the heart graph, False if you just want the summary data.
		:return: A dict containing statistics about the heart data for this particular day.
		:rtype: dict
		"""
		if not(self.cached_heart is None):
			return json.loads(self.cached_heart)

		dts, dte = self.__calculate_wake_time()
		data = {'date': dts.strftime("%a %-d %b %Y"), 'heart': {}}

		data['prev'] = (self.date - datetime.timedelta(days=1)).strftime('%Y%m%d')
		if not(self.today):
			data['next'] = (self.date + datetime.timedelta(days=1)).strftime('%Y%m%d')

		max_rate = float(max_heart_rate(dts))
		zone_1 = int(max_rate * 0.5)
		zone_2 = int(max_rate * 0.5)

		data['heart']['abs_max_rate'] = max_rate

		max = 0
		zone = [0, 0, 0]
		readings = self.data_readings('heart-rate')
		for dr in readings.filter(value__gte=zone_2):
			zone[2] = zone[2] + int((dr.end_time - dr.start_time).total_seconds())
		for dr in readings.filter(value__gte=zone_1):
			zone[1] = zone[1] + int((dr.end_time - dr.start_time).total_seconds())
		zone[2] = zone[1] - zone[2]
		zone[0] = int((dte - dts).total_seconds()) - (zone[1] + zone[2])
		data['heart']['day_max_rate'] = readings.aggregate(m=Max('value'))['m']
		if data['heart']['day_max_rate'] is None:
			data['heart']['day_max_rate'] = 0
		data['heart']['heartzonetime'] = zone
		if graph:
			data['heart']['graph'] = self.get_heart_graph()
			self.cached_heart = json.dumps(data)
			self.save(update_fields=['cached_heart'])

		return data

	def get_heart_graph(self):
		"""
		Returns the stored heart rate values for an entire day, for the purpose of drawing a graph.

		:return: A list of two-value lists consisting of graph co-ordinates, with time on the x-axis and heart rate in bpm on the y-axis.
		:rtype: list
		"""
		dts, dte = self.__calculate_wake_time()

		last = None
		values = {}
		for item in DataReading.objects.filter(start_time__lt=dte, end_time__gte=dts, type='heart-rate').order_by('start_time'):
			dtx = int((item.start_time - dts).total_seconds() / 60)
			if dtx in values:
				if item.value < values[dtx]:
					continue
			values[dtx] = item.value
		ret = []
		for x in range(0, 1440):
			dtx = dts + datetime.timedelta(minutes=x)
			if x in values:
				y = values[x]
				if not(last is None):
					td = (dtx - last).total_seconds()
					if td > 600:
						item = {'x': (last + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
						ret.append(item)
						item = {'x': (dtx - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
						ret.append(item)
				item = {'x': dtx.strftime("%Y-%m-%dT%H:%M:%S"), 'y': y}
				last = dtx
				ret.append(item)

		return(ret)

	def get_sleep_information(self):
		"""
		Returns a summary of the stored sleep data for the day in question.

		:return: A dict containing statistics about the wake and sleep activity for this particular day.
		:rtype: dict
		"""
		dts, dte = self.__calculate_wake_time()
		sleep_data = []

		data = {'date': dts.strftime("%a %-d %b %Y")}
		data['wake_up'] = dts.astimezone(self.timezone).strftime("%Y-%m-%d %H:%M:%S %z")
		data['bedtime'] = dte.astimezone(self.timezone).strftime("%Y-%m-%d %H:%M:%S %z")
		data['wake_up_local'] = dts.astimezone(self.timezone).strftime("%I:%M%p").lstrip("0").lower()
		data['bedtime_local'] = dte.astimezone(self.timezone).strftime("%I:%M%p").lstrip("0").lower()
		data['length'] = (dte - dts).total_seconds()
		data['prev'] = self.yesterday.date.strftime('%Y%m%d')
		if not(self.today):
			data['next'] = self.tomorrow.date.strftime('%Y%m%d')

		if not(self.cached_sleep is None):
			data['sleep'] = json.loads(self.cached_sleep)
			if 'sleep' in data:
				if 'end' in data['sleep']:
					data['tomorrow'] = data['sleep']['end']
			self.wake_time = dts
			self.bed_time = dte
			self.save(update_fields=['wake_time', 'bed_time'])
			return data

		if self.today or self.tomorrow.today:
			for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=dts).order_by('start_time'):
				sleep_data.append(sleep_info)
		else:
			dtee = dts + datetime.timedelta(seconds=86400)
			if self.tomorrow:
				if self.tomorrow.wake_time:
					dtee = self.tomorrow.wake_time
			for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=dts, end_time__lte=dtee).order_by('start_time'):
				sleep_data.append(sleep_info)
		if len(sleep_data) > 0:
			data['sleep'] = parse_sleep(sleep_data)
			if 'end' in data['sleep']:
				data['tomorrow'] = data['sleep']['end']
			self.cached_sleep = json.dumps(data['sleep'])

		if not(self.today):
			self.wake_time = dts
			self.bed_time = dte
			self.save(update_fields=['wake_time', 'bed_time', 'cached_sleep'])

		return data

	def __suntimes(self):
		"""
		Calculates the sun up / down times for this day, based on where the user slept or the
		home location if that isn't available.
		"""
		if not((self.sunrise_time is None) or (self.sunset_time is None)):
			return(self.sunrise_time, self.sunset_time)
		try:
			home = Location.objects.get(pk=settings.USER_HOME_LOCATION)
		except:
			home = None
		if not(home is None):
			wake_loc = (home.lat, home.lon)
			sleep_loc = (home.lat, home.lon)
		if not(self.wake_time is None):
			try:
				wake_loc = get_logged_position(self.wake_time)
			except:
				wake_loc = None
		if not(self.bed_time is None):
			try:
				sleep_loc = get_logged_position(self.bed_time)
			except:
				sleep_loc = wake_loc
		if wake_loc is None:
			return None
		if sleep_loc is None:
			return None
		try:
			sun_wake = SunTimes(wake_loc[1], wake_loc[0])
		except:
			return None
		self.sunrise_time = pytz.utc.localize(sun_wake.riseutc(self.date))
		try:
			sun_sleep = SunTimes(sleep_loc[1], sleep_loc[0])
		except:
			sun_sleep = sun_wake
		self.sunset_time = pytz.utc.localize(sun_sleep.setutc(self.date))
		return(self.sunrise_time, self.sunset_time)

	def refresh(self, save=True):
		"""
		Refreshes the data in the object (regenerating stored properties like wake and sleep time).
		Always called automatically on each Day object created, but may be called manually too.

		:param save: If True, the object's save function is automatically called at the end of this function. If False, it is not.
		"""
		d = self.date
		self.timezone_str = settings.TIME_ZONE
		dts, dte = self.__calculate_wake_time()

		data = getboundingbox(dts, dte)
		if len(data) == 4:
			try:
				tz1 = get_tz(data[0], data[1])
				tz2 = get_tz(data[2], data[3])
				if tz1 == tz2:
					self.timezone_str = tz1
			except:
				pass # Leave at local time if we have an issue

		dts, dte = self.__calculate_wake_time() # Do this again, because the timezone may have changed.
		if not(self.today):
			self.wake_time = dts
			self.bed_time = dte
		suntimes = self.__suntimes()
		try:
			country = Location.objects.get(id=settings.USER_HOME_LOCATION).country.a2
		except:
			country = ''
		if len(country) == 2:
			hols = holidays.country_holidays(country)
			if self.date in hols:
				self.is_public_holiday = True
			else:
				self.is_public_holiday = False

		if save:
			self.cached_heart = None
			self.cached_sleep = None
			self.save()

	def __str__(self):
		return(self.date.strftime('%A, %-d %B %Y'))

	class Meta:
		app_label = 'viewer'
		verbose_name = 'day'
		verbose_name_plural = 'days'

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

class CalendarFeed(models.Model):
	url = models.URLField()
	def __str__(self):
		return(str(self.url))
	class Meta:
		app_label = 'viewer'
		verbose_name = 'calendar'
		verbose_name_plural = 'calendars'

class CalendarTask(models.Model):
	taskid = models.SlugField(max_length=255, blank=True, default='')
	time_due = models.DateTimeField(null=True, blank=True)
	time_created = models.DateTimeField(null=True, blank=True)
	time_completed = models.DateTimeField(null=True, blank=True)
	data = models.TextField(default='', blank=True)
	caption = models.CharField(max_length=255, default='', blank=True)
	description = models.TextField(default='', blank=True)
	created_time = models.DateTimeField(auto_now_add=True)
	updated_time = models.DateTimeField(auto_now=True)
	calendar = models.ForeignKey(CalendarFeed, on_delete=models.CASCADE, related_name='tasks')
	def __str__(self):
		return(self.taskid)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'calendar task'
		verbose_name_plural = 'calendar tasks'
		unique_together = ('taskid', 'calendar')

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
		self.save(update_fields=['cached_staticmap'])
		return im

	def location_text(self):
		if self.cached_locationtext != '':
			return self.cached_locationtext
		ret = get_location_name(self.lat, self.lon)
		if ret != '':
			self.cached_locationtext = ret
			self.save(update_fields=['cached_locationtext'])
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

class LocationCategory(models.Model):
	"""This class represents a category of places. It should normally be used
	for things like 'pub' and 'cinema' but can also be 'friends houses', etc.
	"""
	caption = models.CharField(max_length=255, default='', blank=True)
	locations = models.ManyToManyField(Location, related_name='categories')
	colour = ColorField(default='#777777')
	schema_map = models.ForeignKey(SchemaOrgClass, on_delete=models.SET_NULL, related_name='categories', null=True, blank=True)
	def __str__(self):
		return(self.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'location category'
		verbose_name_plural = 'location categories'

@receiver(pre_save, sender=Day)
def save_day_trigger(sender, instance, **kwargs):
	instance.refresh(save=False)

@receiver(pre_save, sender=Event)
def save_event_trigger(sender, instance, **kwargs):
	instance.refresh(save=False)

class LifeReportProperties(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='properties')
	key = models.CharField(max_length=128)
	value = models.CharField(max_length=255)
	category = models.SlugField(max_length=32, default='')
	icon = models.SlugField(max_length=64, default='bar-chart')
	description = models.TextField(null=True, blank=True)
	def __str__(self):
		return str(self.report) + ' - ' + self.key
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		return {'category': self.category, 'key': self.key, 'value': self.value, 'icon': self.icon, 'description': self.description}
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report property'
		verbose_name_plural = 'life report properties'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['key']),
		]

class LifeReportGraph(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='graphs')
	key = models.CharField(max_length=128)
	data = models.TextField(default='', blank=True)
	category = models.SlugField(max_length=32, default='')
	type = models.SlugField(max_length=16, default='bar')
	icon = models.SlugField(max_length=64, default='bar-chart')
	cached_image = models.ImageField(blank=True, null=True, upload_to=report_graph_upload_location)
	description = models.TextField(null=True, blank=True)
	def image(self, w=640, h=640):
		if ((w == 640) & (h == 640)):
			if self.cached_image:
				im = Image.open(self.cached_image)
				return im
		data = json.loads(self.data)
		ret = None
		if self.type == 'pie':
			ret = generate_pie_chart(data, w, h)
		if self.type == 'donut':
			ret = generate_donut_chart(data, w, h)
		if ret is None:
			return False
		if ((w == 640) & (h == 640)):
			blob = BytesIO()
			ret.save(blob, 'PNG')
			self.cached_image.save(report_graph_upload_location, File(blob), save=False)
			self.save()
		return ret
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		if not self.cached_image:
			im = self.image()
		return {'category': self.category, 'name': self.key, 'image': self.cached_image.path}
	def __str__(self):
		return str(self.report) + ' - ' + self.key
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report graph'
		verbose_name_plural = 'life report graphs'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['type']),
			models.Index(fields=['key']),
		]

class LifeReportChart(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='charts')
	text = models.CharField(max_length=128)
	category = models.SlugField(max_length=32, default='')
	data = models.TextField(default='[]')
	description = models.TextField(null=True, blank=True)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		return json.loads(self.data)
	def __str__(self):
		return str(self.report) + ' - ' + self.text
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report chart'
		verbose_name_plural = 'life report charts'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['text']),
		]
