from django.db import models
from django.core.files import File
from django.db.models import Count, F, Avg, Max, Sum, Transform, Field, IntegerField
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
from colorfield.fields import ColorField
from PIL import Image
from io import BytesIO
from configparser import ConfigParser
from staticmap import StaticMap, Line
from xml.dom import minidom
from dateutil import parser
from tzfpy import get_tz

from viewer.models.places import Location
from viewer.models.people import Person, RemoteInteraction
from viewer.models.misc import DataReading, CalendarAppointment

from viewer.health import parse_sleep, max_heart_rate
from viewer.functions.geo import get_location_name
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

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
		self.save()
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
				self.refresh_geo()
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
		self.save()
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
	def refresh(self):
		for photo in Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time):
			for person in photo.people.all():
				self.people.add(person)
		self.cached_health = ''
		self.save()
	def subevents(self):
		return Event.objects.filter(start_time__gte=self.start_time, end_time__lte=self.end_time).exclude(id=self.id).order_by('start_time')

	def refresh_geo(self):
		id = self.start_time.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + self.end_time.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
		url = settings.LOCATION_MANAGER_URL + "/route/" + id + "?format=json"
		ret = ""
		data = {}
		with urllib.request.urlopen(url) as h:
			data = json.loads(h.read().decode())
		if 'geo' in data:
			if 'geometry' in data['geo']:
				if 'coordinates' in data['geo']['geometry']:
					if len(data['geo']['geometry']['coordinates']) > 0:
						ret = json.dumps(data['geo'])
				if 'geometries' in data['geo']['geometry']:
					if len(data['geo']['geometry']['geometries']) > 0:
						ret = json.dumps(data['geo'])
		self.geo = ret
		self.save()
		return ret
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
		max_hr = float(max_heart_rate(self.start_time))
#		if len(self.cached_health) > 2:
#			return json.loads(self.cached_health)
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
		cum = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
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
			last_time = datetime.datetime.strptime(re.sub('\.[0-9]+', '', speed[0]['x']), "%Y-%m-%dT%H:%M:%S%z")
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
		self.save()
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

class PhotoCollage(models.Model):
	image = models.ImageField(blank=True, null=True)
	event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL, related_name='photo_collages')
	photos = models.ManyToManyField(Photo, related_name='photo_collages')
	def __str__(self):
		if self.event is None:
			return 'Unknown Event'
		else:
			return str(self.event.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'photo collage'
		verbose_name_plural = 'photo collages'

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

class Media(models.Model):
	type = models.SlugField(max_length=16)
	unique_id = models.SlugField(max_length=128)
	label = models.CharField(max_length=255)

class MediaEvent(models.Model):
	media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="events")
	time = models.DateTimeField()

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

	@property
	def today(self):
		"""
		Determines if this day represents today in real time.
		"""
		return (datetime.datetime.now().date() == self.date)
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
		dts = datetime.datetime(d.year, d.month, d.day, 4, 0, 0, tzinfo=self.timezone)
		dte = dts + datetime.timedelta(seconds=86400)
		return Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by('start_time')
	@property
	def calendar(self):
		"""
		Every calendar appointment scheduled on this particular day.
		"""
		d = self.date
		dts = datetime.datetime(d.year, d.month, d.day, 4, 0, 0, tzinfo=self.timezone)
		dte = dts + datetime.timedelta(seconds=86400)
		return CalendarAppointment.objects.filter(end_time__gte=dts, start_time__lte=dte).values('id', 'eventid', 'caption')
	@property
	def tweets(self):
		"""
		Every microblogpost (typically tweets, could be toots) made on this particular day.
		"""
		d = self.date
		dts = datetime.datetime(d.year, d.month, d.day, 4, 0, 0, tzinfo=self.timezone)
		dte = dts + datetime.timedelta(seconds=86400)
		return RemoteInteraction.objects.filter(time__gte=dts, time__lte=dte, type='microblogpost', address='').order_by('time')
	@property
	def sms(self):
		"""
		Every SMS message sent or received on this particular day.
		"""
		d = self.date
		dts = datetime.datetime(d.year, d.month, d.day, 4, 0, 0, tzinfo=self.timezone)
		dte = dts + datetime.timedelta(seconds=86400)
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
		obj = DataReading.objects.filter(type='mood').filter(start_time__gte=dts, end_time__lt=dte).aggregate(mood=Avg('value'))
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

	def __calculate_wake_time(self):

		d = self.date
		dts = datetime.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=self.timezone)
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
			return dts.astimezone(self.timezone), dte.astimezone(self.timezone)

	def refresh(self, save=True):
		"""
		Refreshes the data in the object (regenerating stored properties like wake and sleep time).
		Always called automatically on each Day object created, but may be called manually too.

		:param save: If True, the object's save function is automatically called at the end of this function. If False, it is not.
		"""
		d = self.date
		self.timezone_str = settings.TIME_ZONE
		dts, dte = self.__calculate_wake_time()

		id = dts.strftime("%Y%m%d%H%M%S") + dte.strftime("%Y%m%d%H%M%S")
		url = settings.LOCATION_MANAGER_URL + "/bbox/" + id + "?format=json"
		data = []
		with urllib.request.urlopen(url) as h:
			data = json.loads(h.read().decode())
		if len(data) == 4:
			try:
				tz1 = get_tz(data[0], data[1])
				tz2 = get_tz(data[2], data[3])
				if tz1 == tz2:
					self.timezone_str = tz1
			except:
				pass # Leave at local time if we have an issue

		if not(self.today):
			self.wake_time = dts
			self.bed_time = dte

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

@receiver(pre_save, sender=Day)
def save_day_trigger(sender, instance, **kwargs):
	instance.refresh(save=False)
