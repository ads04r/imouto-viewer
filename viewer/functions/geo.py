import datetime, pytz, json, urllib.request, re, sys, os
from viewer.models import *
from django.conf import settings

def convert_to_degrees(value):

	try:
		d = float(value.values[0].num) / float(value.values[0].den)
	except:
		d = 0.0
	try:
		m = float(value.values[1].num) / float(value.values[1].den)
	except:
		m = 0.0
	try:
		s = float(value.values[2].num) / float(value.values[2].den)
	except:
		s = 0.0

	return d + (m / 60.0) + (s / 3600.0)

def getgeoline(dts, dte, loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/route/" + id + "?format=json"
	data = {}
	with urllib.request.urlopen(url) as h:
		data = json.loads(h.read().decode())
	if 'geo' in data:
		if 'geometry' in data['geo']:
			if 'coordinates' in data['geo']['geometry']:
				if len(data['geo']['geometry']['coordinates']) > 0:
					return json.dumps(data['geo'])
	return ""

def getelevation(dts, dte, loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/elevation/" + id + "?format=json"
	data = []
	with urllib.request.urlopen(url) as h:
		for item in json.loads(h.read().decode()):
			data.append({'x': item[1], 'y': item[2]})
	if len(data) > 0:
		return json.dumps(data)
	return ""

def getspeed(dts, dte, loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/elevation/" + id + "?format=json"
	data = []
	last_dist = 0
	last_time = dts
	with urllib.request.urlopen(url) as h:
		for item in json.loads(h.read().decode()):
			dt = datetime.datetime.strptime(re.sub('\.[0-9]+', '', item[0]), "%Y-%m-%dT%H:%M:%S%z")
			time_diff = (dt - last_time).total_seconds()
			dist_diff = item[1] - last_dist
			speed = 0
			if time_diff > 0:
				speed = ((dist_diff / 1609.344) / (time_diff / 3600))
			data.append({'x': item[0], 'y': speed})
			last_time = dt
			last_dist = item[1]
	if len(data) > 0:
		return json.dumps(data)
	return ""
