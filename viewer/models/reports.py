from django.db import models
from django.core.files import File
from django.db.models import Count, Field, IntegerField, F
from django.conf import settings
from django.utils.html import strip_tags
from PIL import Image
from io import BytesIO
from wordcloud import WordCloud, STOPWORDS

from viewer.models.places import Location
from viewer.models.people import Person
from viewer.models.core import Event, Photo

from viewer.staticcharts import generate_pie_chart, generate_donut_chart
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

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
		for chart in LifeReportGraph.objects.filter(report=self):
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
		dts = datetime.datetime(self.year, 1, 1, 0, 0, 0, tzinfo=tz)
		dte = datetime.datetime(self.year, 12, 31, 23, 59, 59, tzinfo=tz)
		subevents = []
		self.events.clear()
		self.cached_dict = None
		self.save()
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
		self.save()
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
				dts = datetime.datetime(year, (i + 1), 1, 0, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
				if i < 11:
					dte = datetime.datetime(year, (i + 2), 1, 0, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE)) - datetime.timedelta(seconds=1)
				else:
					dte = datetime.datetime((year + 1), 1, 1, 0, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE)) - datetime.timedelta(seconds=1)
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
		self.save()
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
