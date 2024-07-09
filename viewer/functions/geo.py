import datetime, pytz, json, re, sys, os, requests
from django.core.cache import cache
from django.conf import settings
from geopy import distance
from frechetdist import frdist

import logging
logger = logging.getLogger(__name__)

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
	r = requests.get(url)
	data = json.loads(r.text)
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
		r = requests.get(url)
		data = json.loads(r.text)
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

def __get_location_property(lat, lon, property, loctype='country'):

	cache_key = "address_" + str(lat) + "," + str(lon)
	data = cache.get(cache_key)
	try:
		mapbox_key = settings.MAPBOX_API_KEY
	except:
		return ''
	if data is None:
		url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + str(lon) + "," + str(lat) + ".json?language=en&access_token=" + mapbox_key
		r = requests.get(url)
		data = json.loads(r.text)
		if not('features' in data):
			return ''
		cache.set(cache_key, data, timeout=86400)
	if not('features' in data):
		return ''
	for f in data['features']:
		if not(loctype in f['place_type']):
			continue
		if 'properties' in f:
			if 'short_code' in f['properties']:
				return str(f['properties'][property])
	return ''

def get_location_country_code(lat, lon):
	"""
	Given a point, returns the ISO-3166-1 alpha-2 country code.

	:param lat: The latitude of the point.
	:param lon: The longitude of the point.
	:return: A string containing the country code, if possible, empty string if not.
	:rtype: str

	"""
	ret = __get_location_property(lat, lon, 'short_code', 'country').upper()
	if len(ret) == 2:
		return ret
	return ''

def get_location_wikidata_id(lat, lon, loctype='country'):
	"""
	Given a point, returns the Wikidata ID for the area type specified, default is country.

	:param lat: The latitude of the point.
	:param lon: The longitude of the point.
	:param loctype: The type of area for which to get the Wikidata ID.
	:return: A string containing the country code, if possible, empty string if not.
	:rtype: str

	"""
	return __get_location_property(lat, lon, 'wikidata', loctype)

def get_location_address_fragment(lat, lon, fragment='country'):
	"""
	Given a point, returns the most specific human-readable name for the area that matches the type given by fragment.

	:param lat: The latitude of the point.
	:param lon: The longitude of the point.
	:param fragment: The type of address fragment we are after, eg 'country' or 'city'.
	:return: A string containing a name for the area.
	:rtype: str

	"""
	cache_key = "address_" + str(lat) + "," + str(lon)
	data = cache.get(cache_key)
	try:
		mapbox_key = settings.MAPBOX_API_KEY
	except:
		return ''
	if data is None:
		url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + str(lon) + "," + str(lat) + ".json?language=en&access_token=" + mapbox_key
		r = requests.get(url)
		data = json.loads(r.text)
		if not('features' in data):
			return ''
		cache.set(cache_key, data, timeout=86400)
	if not('features' in data):
		return ''
	for f in data['features']:
		if not(fragment in f['place_type']):
			continue
		if 'text_en' in f:
			return f['text_en']
		if 'place_name_en' in f:
			return f['place_name_en']
		if 'text' in f:
			return f['text']
		if 'place_name' in f:
			return f['place_name']
	return ''

def stretch_array(source_array, target_length):
	ret = []
	source_length = len(source_array)
	extend_by = target_length - source_length
	if extend_by <= 0:
		return source_array
	c = int(source_length / (extend_by + 1))
	j = 0
	for i in range(0, source_length):
		ret.append(source_array[i])
		j = j + 1
		if j > c:
			j = 0
			ret.append(source_array[i])
	return ret

def journey_similarity(event1, event2):
	"""
	Uses the frechedist library to compute the similarity between the routes of two journey events.

	:param event1: The first event to be compared.
	:param event2: The second event to be compared.
	:return: A value between 0 (routes are identical) and 100 (routes couldn't be more different)
	:rtype: float

	"""
	ec1 = event1.simplified_coordinates()
	ec2 = event2.simplified_coordinates()
	l1 = len(ec1)
	l2 = len(ec2)
	if l1 == 0:
		return 100.0
	if l2 == 0:
		return 100.0
	if l1 != l2:
		return 100.0
	if l1 != 100:
		return 100.0
	return frdist(ec1, ec2)

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

