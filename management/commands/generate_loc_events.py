from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import Event, Location
from viewer.functions import nearest_location
import os, sys, datetime, pytz, csv, socket, json, urllib, re, random, sys, urllib.request

class Command(BaseCommand):
	"""
	Command for generating location events from existing GPS data.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-l", "--min-length", action="store", dest="minlength", default="300", help="The minimum length (in seconds) that an event can be. Any period of time spent at a location for less than this is ignored.")

	def handle(self, *args, **kwargs):

		url = settings.LOCATION_MANAGER_URL + '/process'
		r = urllib.request.urlopen(url)
		data = json.loads(r.read())
		dts = Event.objects.filter(type='loc_prox').exclude(caption='Home').order_by('-start_time')[0].start_time.replace(hour=0, minute=0, second=0)
		dte = datetime.datetime.fromtimestamp(int(data['stats']['last_calculated_positon'])).replace(tzinfo=pytz.UTC)
		max_duration = kwargs['minlength']

		duration = int(((dte - dts).total_seconds()) / (60 * 60 * 24))
		mils = re.compile(r"\.([0-9]+)")

		for i in range(0, duration + 1):
			dt = dts + datetime.timedelta(days=i)
			url = settings.LOCATION_MANAGER_URL + "/route/" + dt.strftime("%Y%m%d") + '000000' + dt.strftime("%Y%m%d") + "235959?format=json"
			data = []
			with urllib.request.urlopen(url) as h:
				data = json.loads(h.read().decode())
			if not('geo' in data):
				continue
			if not('bbox' in data['geo']):
				continue

			lat1 = data['geo']['bbox'][1]
			lat2 = data['geo']['bbox'][3]
			lon1 = data['geo']['bbox'][0]
			lon2 = data['geo']['bbox'][2]
			if lat1 > lat2:
				lat1 = data['geo']['bbox'][3]
				lat2 = data['geo']['bbox'][1]
			if lon1 > lon2:
				lon1 = data['geo']['bbox'][2]
				lon2 = data['geo']['bbox'][0]
			for location in Location.objects.filter(lon__gte=lon1, lon__lte=lon2, lat__gte=lat1, lat__lte=lat2):
				url = settings.LOCATION_MANAGER_URL + "/event/" + dt.strftime("%Y-%m-%d") + "/" + str(location.lat) + "/" + str(location.lon) + "?format=json"
				data = []
				try:
					with urllib.request.urlopen(url) as h:
						data = json.loads(h.read().decode())
				except:
					sys.stderr.write("Reading " + url + " failed\n")
					data = []
				if len(data) == 0:
					continue
				for item in data:
					dtstart = datetime.datetime.strptime(mils.sub("", item['timestart']), "%Y-%m-%dT%H:%M:%S%z")
					dtend = datetime.datetime.strptime(mils.sub("", item['timeend']), "%Y-%m-%dT%H:%M:%S%z")
					dtlen = (dtend - dtstart).total_seconds()
					if dtlen < max_duration:
						continue
					if location.label == 'Home':
						continue
					if Event.objects.filter(start_time__lte=dtstart, end_time__gte=dtend).count() > 0:
						continue
					if Event.objects.filter(start_time__lte=dtend, end_time__gte=dtstart).exclude(type='journey').count() > 0:
						continue
					print(str(dtstart) + " - " + str(location) + " " + str(int(dtlen / 60)))
					ev = Event(caption=location.label, location=location, start_time=dtstart, end_time=dtend, type='loc_prox')
					ev.save()
