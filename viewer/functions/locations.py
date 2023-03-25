import datetime, pytz, json, re, sys, os, requests
from viewer.models import *
from viewer.functions.calendar import event_label
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

def create_location_events(minlength=300):

	try:
		home_id = settings.USER_HOME_LOCATION
	except:
		home_id = -1
	dts = Event.objects.filter(type='loc_prox').exclude(location__id=home_id).order_by('-start_time')[0].start_time
	dte = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC) + datetime.timedelta(days=1)
	ret = []
	while dts < dte:
		url = settings.LOCATION_MANAGER_URL + '/event/' + dts.strftime("%Y-%m-%d")
		dt_check = dts.replace(hour=0, minute=0, second=0)
		dts = dts + datetime.timedelta(days=1)

		r = requests.get(url)
		data = json.loads(r.text)
		last_item = ''
		for item in data:
			if item['timestart'] == last_item:
				continue
			last_item = item['timestart']

			loc = nearest_location(item['lat'], item['lon'])
			if loc == None:
				continue
			if loc.pk == home_id:
				continue

			start_time = parser.parse(item['timestart'])
			end_time = parser.parse(item['timeend'])
			dist = distance.distance((item['lat'], item['lon']), (loc.lat, loc.lon)).km * 1000
			dur = (end_time - start_time).total_seconds()

			if start_time < dt_check:
				continue
			if dist > 50:
				continue
			if dur < minlength:
				continue

			caption = event_label(start_time, end_time)
			if caption == '':
				caption = loc.label

			ev = Event(caption=caption, location=loc, start_time=start_time, end_time=end_time, type='loc_prox')
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
	r = requests.get(url)
	data = json.loads(r.text)

	ret = []

	for item in data:
		if item['timestart'] == item['timeend']:
			continue
		ret.append({'start_time': parser.parse(item['timestart']), 'end_time': parser.parse(item['timeend'])})

	return ret
