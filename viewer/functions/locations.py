import datetime, pytz, overpy, requests
from viewer.models import Location, Event, LocationCity, LocationCountry
from viewer.functions.calendar import event_label
from viewer.functions.location_manager import getstopevents
from django.conf import settings
from geopy import distance
from dateutil import parser
from urllib.parse import urlencode
from iso3166 import countries as isocountries

import logging
logger = logging.getLogger(__name__)

def home_location():
	"""
	Return the user's home location from settings (as a Location object, rather than the primary key as an integer)
	:return: The home location, or None if not set
	:rtype: Location
	"""
	try:
		return Location.objects.get(pk=settings.USER_HOME_LOCATION)
	except AttributeError:
		return None

def nearest_location(lat, lon):
	"""
	Return the nearest known location to the query position given.

	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:return: The nearest location.
	:rtype: Location

	"""
	now = pytz.utc.localize(datetime.datetime.utcnow())
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

def nearest_amenities(lat, lon, dist=50):
	"""
	Query OpenStreetMap to get the nearest amenities to the point specified.

	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:param dist: The distance from the query point to search.
	:return: A list of dictionaries, each representing an amenity listed in OpenStreetMap.
	:rtype: list

	"""
	query = "nwr[amenity](around:" + str(dist) + "," + str(lat) + "," + str(lon) + "); out;"
	api = overpy.Overpass()
	result = api.query(query)
	ret = []
	for node in result.nodes:
		item = dict(node.tags)
		if 'name' in item:
			item['lat'] = float(node.lat)
			item['lon'] = float(node.lon)
			ret.append(item)
	return ret

def nearest_city(lat, lon):
	"""
	Return the nearest known city to the query position given.

	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:return: The nearest city.
	:rtype: LocationCity

	"""
	dist = 99999.9
	ret = None
	check = (lat, lon)
	for loc in LocationCity.objects.all():
		test = (loc.lat, loc.lon)
		newdist = distance.distance(test, check).km
		if newdist < dist:
			dist = newdist
			ret = loc
	return ret

def create_location_events(minlength=300):
	"""
	Create a set of location events based on the no-movement periods generated by the Location Manager.

	:param minlength: The minimum length of a location event in seconds. Events shorter than this will not be created. Default is 300 seconds (5 minutes).
	:return: The newly created events as a list ordered chronologically.
	:rtype: list[Event]

	"""
	try:
		home_id = settings.USER_HOME_LOCATION
	except:
		home_id = -1
	dts = Event.objects.filter(type='loc_prox').exclude(location__id=home_id).order_by('-start_time')[0].start_time
	dte = pytz.utc.localize(datetime.datetime.utcnow()).replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
	ret = []
	while dts < dte:
		logger.debug("Checking stop events")
		data = getstopevents(dts)
		dt_check = dts.replace(hour=0, minute=0, second=0)
		dts = dts + datetime.timedelta(days=1)

		last_item = ''
		for item in data:
			logger.debug("   Found event from " + item['timestart'])
			if item['timestart'] == last_item:
				logger.debug("      ...ignoring")
				continue
			last_item = item['timestart']

			logger.debug("      ...searching for nearest location to " + str(item['lat']) + ', ' + str(item['lon']))
			loc = nearest_location(item['lat'], item['lon'])
			if loc == None:
				logger.debug("         ...None returned, skipping")
				continue
			if loc.pk == home_id:
				logger.debug("         ...matches home")
				continue
			logger.debug("         ...matches " + str(loc))

			start_time = parser.parse(item['timestart'])
			end_time = parser.parse(item['timeend'])
			dist = distance.distance((item['lat'], item['lon']), (loc.lat, loc.lon)).km * 1000
			dur = (end_time - start_time).total_seconds()

			if start_time < dt_check:
				logger.debug("            start time is before " + str(dt_check) + ", skipping")
				continue
			if dist > 90:
				logger.debug("            " + str(dist) + "m away, skipping")
				continue
			if dur < minlength:
				logger.debug("            event is less than " + str(minlength) + " seconds, skipping")
				continue
			if Event.objects.filter(start_time__gte=start_time, start_time__lte=start_time).count() > 0:
				logger.debug("            existing event(s) intersect, skipping")
				continue
			if Event.objects.filter(end_time__gte=start_time, end_time__lte=start_time).count() > 0:
				logger.debug("            existing event(s) intersect, skipping")
				continue
			if Event.objects.filter(start_time__lte=end_time, end_time__gte=start_time).count() > 0:
				logger.debug("            existing event(s) intersect, skipping")
				continue

			caption = event_label(start_time, end_time)
			if caption == '':
				caption = loc.label

			logger.debug("            creating event")
			try:
				ev = Event.objects.get(start_time=start_time, end_time=end_time, type='loc_prox')
			except:
				ev = None
			if ev is None:
				ev = Event(caption=caption, location=loc, start_time=start_time, end_time=end_time, type='loc_prox')
				ret.append(ev)
				ev.save()

	return ret

def join_location_events(event1, event2):
	"""
	Creates a journey event between two location events.

	:param event1: The id of an event. This event must end before event2 starts.
	:param event2: The id of an event. This event must start after event1 ends.
	:return: The newly generated journey event.
	:rtype: Event

	"""
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
	geo = event.geo
	event.health()
	del geo

	return event

def distance_waffle(dist_value):
	"""
	Returns a human readable string illustrating a large distance relative to the home location.

	:param dist_value: A distance, in miles.
	:return: A string, for example, "Further than the distance to Warsaw".
	:rtype: str

	"""
	try:
		home = Location.objects.get(pk=settings.USER_HOME_LOCATION)
	except:
		return ""
	homeloc = (home.lat, home.lon)
	ret = {"dist": 0.0}
	for city in LocationCity.objects.all():
		pos = (float(city.lat), float(city.lon))
		dist = distance.distance(homeloc, pos).miles
		if dist > dist_value:
			continue
		if dist < ret['dist']:
			continue
		ret = {"city": city, "dist": dist}
	if not('city' in ret):
		return str(dist_value) + " miles"
	city = ret['city']
	if city.country:
		return "Further than the distance to " + city.label + ", " + city.country.label + " (" + str(int(ret['dist'])) + " miles)"
	else:
		return "Further than the distance to " + city.label + " (" + str(int(ret['dist'])) + " miles)"


def fill_country_cities():

	api = overpy.Overpass()
	ret = LocationCity.objects.count()
	for country in LocationCountry.objects.exclude(locations=None):
		query = 'area["name:en"="' + country.label + '"]->.country;node[place=city](area.country);out;'
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
				if len(parse) >= 2:
					wikipedia = "https://" + parse[0] + ".wikipedia.org/wiki/" + parse[1]
			if not('en.wikipedia.org') in wikipedia:
				wikipedia = ''
			try:
				city = LocationCity.objects.get(label=city_name)
			except:
				city = LocationCity(label=city_name, country=country, lat=lat, lon=lon)
			if city.wikipedia is None:
				if len(wikipedia) > 0:
					city.wikipedia = wikipedia
			try:
				city.save()
			except:
				continue
	ret = LocationCity.objects.count() - ret
	return ret

def fill_location_cities():

	ret = 0
	for loc in Location.objects.filter(city=None).exclude(country=None):
		address = [x.strip() for x in str(loc.address).split(',')]
		city = nearest_city(loc.lat, loc.lon)
		if ((city.label in address) & (loc.country == city.country)):
			loc.city = city
			ret = ret + 1
			loc.save(update_fields=['city'])
	return ret

def fill_location_countries():

	ret = 0
	for loc in Location.objects.filter(country=None):
		address = [x.strip() for x in str(loc.address).split(',')]
		city = nearest_city(loc.lat, loc.lon)
		if city.country:
			if city.country.label in address:
				loc.country = city.country
				ret = ret + 1
				loc.save(update_fields=['country'])
	return ret

def lookup_address(query):

	if len(query) == 0:
		return []
	url = "https://nominatim.openstreetmap.org/search?" + urlencode({'q': query, 'format': 'json'})
	with requests.get(url, headers={'User-Agent': settings.USER_AGENT}, allow_redirects=True) as r:
		data = r.json()
	return data

def import_countries():

	for c in isocountries:
		try:
			country = LocationCountry.objects.get(a2=c.alpha2)
		except:
			country = None
		if not country is None:
			continue
		country = LocationCountry(a2=c.alpha2, a3=c.alpha3, label=c.name)
		url = "https://en.wikipedia.org/wiki/" + str(c.name).replace(' ', '_')
		with requests.get(url) as r:
			if r.status_code == 200:
				country.wikipedia = url
		country.cached_description = ''
		country.save()
