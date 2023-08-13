import datetime, pytz, json, urllib.request, re, sys, os
import Fred as fred
from django.core.cache import cache
from viewer.models import *
from django.conf import settings
from geopy import distance

def get_location_name(lat, lon):
	"""
	Given a query point, returns a human-readable name for the location.

	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:return: A string containing a name for the location.
	:rtype: str

	"""
	cache_key = "loc_" + str(lat) + "," + str(lon)
	ret = cache.get(cache_key)
	if ret is None:
		ret = ''
	try:
		mapbox_key = settings.MAPBOX_API_KEY
	except:
		return ""
	url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + str(lon) + "," + str(lat) + ".json?language=en&access_token=" + mapbox_key
	r = urllib.request.urlopen(url)
	data = json.loads(r.read())
	if 'features' in data:
		if len(data['features']) > 0:
			if 'text' in data['features'][0]:
				ret = data['features'][0]['text']
	if len(ret) > 0:
		cache.set(cache_key, ret, timeout=86400)
	return ret

def get_area_address(n, w, s, e):
	"""
	Given a query bounding box, returns the most specific human-readable address for the area, as a list.

	:param n: The most northern latitude of the area.
	:param w: The most westerly longitude of the area.
	:param s: The most southern latitude of the area.
	:param e: The most easterly longitude of the area.
	:return: A list of strings containing an address for the area.
	:rtype: list(str)

	"""
	cache_key = "loc_" + str(n) + "," + str(w) + "," + str(s) + "," + str(e)
	ret = cache.get(cache_key)
	if ret is None:
		ret = []
	if len(ret) > 0:
		return ret
	try:
		mapbox_key = settings.MAPBOX_API_KEY
	except:
		return []
	queries = [[w, n], [e, n], [w, s], [e, s]]
	text = []
	c = 50
	for query in queries:
		lon = query[0]
		lat = query[1]
		url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + str(lon) + "," + str(lat) + ".json?language=en&access_token=" + mapbox_key
		r = urllib.request.urlopen(url)
		data = json.loads(r.read())
		addr = []
		if 'features' in data:
			if len(data['features']) > 0:
				for f in reversed(data['features']):
					if not('place_type') in f:
						continue
					if 'postcode' in f['place_type']:
						continue
					if not('text' in f):
						continue
					addr.append(f['text'])
		l = len(addr)
		if l > 0:
			if l < c:
				c = l
			text.append(addr)
	label = ''
	ix = -1

	for i in range(0, c):
		check = []
		for j in range(0, 4):
			try:
				item = text[j][i]
			except:
				item = ''
			if item in check:
				continue
			check.append(item)
		if len(check) == 1:
			if i > ix:
				ix = i

	try:
		ret = list(reversed(text[0][0:(ix + 1)]))
	except:
		ret = []
	cache.set(cache_key, ret, timeout=86400)
	return ret

def get_area_name(n, w, s, e):
	"""
	Given a query bounding box, returns the most specific human-readable name for the area.

	:param n: The most northern latitude of the area.
	:param w: The most westerly longitude of the area.
	:param s: The most southern latitude of the area.
	:param e: The most easterly longitude of the area.
	:return: A string containing a name for the area.
	:rtype: str

	"""
	addr = get_area_address(n, w, s, e)
	if len(addr) == 0:
		return ''
	return addr[0]

def journey_similarity(event1, event2):
	"""
	Uses the Fred library to compute the similarity between the routes of two journey events.

	:param event1: The first event to be compared.
	:param event2: The second event to be compared.
	:return: A value between 0 (routes are identical) and 100 (routes couldn't be more different)
	:rtype: float

	"""
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
		return 100.0
	p1 = (ec1[0][0], ec1[0][1])
	p2 = (ec2[0][0], ec2[0][1])
	p3 = (ec1[-1][0], ec1[-1][1])
	p4 = (ec2[-1][0], ec2[-1][1])
	start_dist = distance.distance(p1, p2).miles
	end_dist = distance.distance(p3, p4).miles
	if start_dist > 1.5:
		return 100.0
	if end_dist > 1.5:
		return 100.0

	c1 = fred.Curve(ec1)
	c2 = fred.Curve(ec2)
	diff = ((fred.continuous_frechet(c1, c2).value) * 100)

	return diff

def convert_to_degrees(value):
	"""
	Converts a value in degrees, minutes and seconds into decimal degrees.

	:param value: The value to convert, as exported from an image file using the exifread function.
	:return: A value representing degrees in decimal form.
	:rtype: float

	"""
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
	"""
	Queries the location manager for the user's position at a particular time.

	:param dt: A Python datetime representing the time being queried.
	:param loc_manager: (Optional) The URL of an Imouto Location Manager server. If omitted, we use the LOCATION_MANAGER_URL setting.
	:return: The raw output from the location manager, which should be a dict containing values for lat, lon, speed, etc.
	:rtype: dict

	"""
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
	"""
	Queries the location manager for the user's route between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:param loc_manager: (Optional) The URL of an Imouto Location Manager server. If omitted, we use the LOCATION_MANAGER_URL setting.
	:return: The raw output from the location manager, which should be a dict containing GeoJSON polyline, among other things.
	:rtype: dict

	"""
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
			if 'geometries' in data['geo']['geometry']:
				if len(data['geo']['geometry']['geometries']) > 0:
					return json.dumps(data['geo'])
	return ""

def getelevation(dts, dte, loc_manager=None):
	"""
	Queries the location manager for the user's elevation between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:param loc_manager: (Optional) The URL of an Imouto Location Manager server. If omitted, we use the LOCATION_MANAGER_URL setting.
	:return: A list containing a sequence of two-element {x, y} dicts, useful for drawing an elevation graph.
	:rtype: list

	"""
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
	"""
	Queries the location manager for the user's speed between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:param loc_manager: (Optional) The URL of an Imouto Location Manager server. If omitted, we use the LOCATION_MANAGER_URL setting.
	:return: A list containing a sequence of two-element {x, y} dicts, useful for drawing a graph with speed on the y-axis and time on the x-axis.
	:rtype: list

	"""
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
