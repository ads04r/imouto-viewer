import datetime, pytz, json, urllib.request, re, sys, os
from viewer.models import *
from django.conf import settings
from geopy import distance
from dateutil import parser

def nearest_location(lat, lon):
	now = datetime.datetime.now().replace(tzinfo=pytz.UTC)
	dist = 99999.9
	ret = None
	check = (lat, lon)
	for loc in Location.objects.exclude(destruction_time__lt=now).exclude(creation_time__gt=now):
		test = (loc.lat, loc.lon)
		newdist = distance.distance(test, check).km
		if newdist < dist:
			dist = newdist
			ret = loc
	return ret

def generate_location_events(minlength):

	url = settings.LOCATION_MANAGER_URL + '/process'
	r = urllib.request.urlopen(url)
	data = json.loads(r.read())
	dts = Event.objects.filter(type='loc_prox').exclude(caption='Home').order_by('-start_time')[0].start_time.replace(hour=0, minute=0, second=0)
	dte1 = datetime.datetime.fromtimestamp(int(data['stats']['last_calculated_position'])).replace(tzinfo=pytz.UTC)
	dte2 = Event.objects.all().order_by('-end_time')[0].end_time
	if dte1 > dte2:
		dte = dte1
	else:
		dte = dte2
	min_duration = int(minlength)

	ret = []

	duration = int(((dte - dts).total_seconds()) / (60 * 60 * 24))
	mils = re.compile(r"\.([0-9]+)")

	for i in range(0, duration + 1):
		dt = dts + datetime.timedelta(days=i)
		dtt = dt + datetime.timedelta(days=1)
		url = settings.LOCATION_MANAGER_URL + "/route/" + dt.strftime("%Y%m%d") + '040000' + dtt.strftime("%Y%m%d") + "040000?format=json"
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

			if not(location.destruction_time is None):
				if location.destruction_time < dt:
					continue

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
				if dtlen < min_duration:
					continue
				if location.label == 'Home':
					continue
				if Event.objects.filter(start_time__lte=dtstart, end_time__gte=dtend).count() > 0:
					continue
				if Event.objects.filter(start_time__lte=dtend, end_time__gte=dtstart).exclude(type='journey').count() > 0:
					continue

				ev = Event(caption=location.label, location=location, start_time=dtstart, end_time=dtend, type='loc_prox')
				ret.append(ev)
				ev.save()

	return ret

def join_location_events(event1, event2):

	try:
		ev1 = Event.objects.get(id=event1)
		ev2 = Event.objects.get(id=event2)
	except:
		return None

	if ev2.end_time < ev1.start_time:
		evt = ev1
		ev1 = ev2
		ev2 = evt

	caption = 'Journey'
	if ev2.location:
		caption = 'Journey to ' + str(ev2.location)
		if ev1.location:
			caption = 'Journey from ' + str(ev1.location) + ' to ' + str(ev2.location)

	event = Event(caption=caption, type='journey', start_time=(ev1.end_time - datetime.timedelta(minutes=1)), end_time=(ev2.start_time + datetime.timedelta(minutes=1)))
	event.save()
	geo = event.refresh_geo()
	health = event.health()

	return event

def get_possible_location_events(date, lat, lon):

	ds = date.strftime("%Y-%m-%d")
	url = settings.LOCATION_MANAGER_URL + '/event/' + ds + '/' + str(lat) + '/' + str(lon)
	r = urllib.request.urlopen(url)
	data = json.loads(r.read())
	ret = []

	for item in data:
		if item['timestart'] == item['timeend']:
			continue
		ret.append({'start_time': parser.parse(item['timestart']), 'end_time': parser.parse(item['timeend'])})

	return ret
