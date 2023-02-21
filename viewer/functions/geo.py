import datetime, pytz, json, urllib.request, re, sys, os
import Fred as fred
from django.core.cache import cache
from viewer.models import *
from django.conf import settings
from geopy import distance

def get_location_name(lat, lon):
	cache_key = "loc_" + str(lat) + "," + str(lon)
	ret = cache.get(cache_key)
	if ret is None:
		ret = ''
	try:
		mapbox_key = settings.MAPBOX_API_KEY
	except:
		return ""
	url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + str(lon) + "," + str(lat) + ".json?access_token=" + mapbox_key
	r = urllib.request.urlopen(url)
	data = json.loads(r.read())
	if 'features' in data:
		if len(data['features']) > 0:
			if 'text' in data['features'][0]:
				ret = data['features'][0]['text']
	if len(ret) > 0:
		cache.set(cache_key, ret, timeout=86400)
	return ret

def journey_similarity(event1, event2):

	ec1 = event1.coordinates()
	ec2 = event2.coordinates()
	if len(ec1) == 0:
		return 100.0
	if len(ec2) == 0:
		return 100.0
	d1 = event1.distance()
	d2 = event2.distance()
	ddiff = abs(d1 - d2)
	if ddiff > 5:
		return 100

	c1 = fred.Curve(ec1)
	c2 = fred.Curve(ec2)
	diff = ((fred.continuous_frechet(c1, c2).value) * 100)

	return diff

def distance_waffle(dist_value):

	home = Location.objects.get(pk=settings.USER_HOME_LOCATION)
	homeloc = (home.lat, home.lon)
	ret = {"dist": 0.0}
	for city in settings.CITY_LOCATIONS:
		pos = (float(city['lat']), float(city['lon']))
		dist = distance.distance(homeloc, pos).miles
		if dist > dist_value:
			continue
		if dist < ret['dist']:
			continue
		ret = {"city": city, "dist": dist}
	return "Further than the distance to " + (", ".join([ret['city']['capital'], ret['city']['country']])) + " (" + str(int(ret['dist'])) + " miles)"

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

def getposition(dt, loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address

	id = dt.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/position/" + id + "?format=json"
	data = {}
	with urllib.request.urlopen(url) as h:
		try:
			data = json.loads(h.read().decode())
		except:
			data = {}
	return data

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
