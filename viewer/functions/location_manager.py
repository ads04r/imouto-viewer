from django.core.cache import cache
from geopy import distance
from django.conf import settings
from dateutil import parser
import datetime, pytz, json, re, sys, os, requests
import Fred as fred

def get_logged_position(dt):
	"""
	Given a date, returns the point that the user was near at the time specified.

	:param date: A datetime.
	:return: A tuple (lat, lon) indicating the user's position
	:rtype: tuple(float)

	"""
	ds = dt.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = settings.LOCATION_MANAGER_URL + '/position/' + ds
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = {}
	if(('lat' in data) & ('lon' in data)):
		return (data['lat'], data['lon'])

	return (None, None)

def get_possible_location_events(date, lat, lon):
	"""
	Given a date and a query point, returns a list of times the user was near the query point on the day specified.

	:param date: A date (not datetime).
	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:return: A list of dictionaries containing start_time and end_time of potential events.
	:rtype: list[dict]

	"""
	ds = date.strftime("%Y-%m-%d")
	url = settings.LOCATION_MANAGER_URL + '/event/' + ds + '/' + str(lat) + '/' + str(lon)
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = []

	ret = []

	for item in data:
		if item['timestart'] == item['timeend']:
			continue
		ret.append({'start_time': parser.parse(item['timestart']), 'end_time': parser.parse(item['timeend'])})

	return ret

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
	try:
		with requests.get(url) as r:
			data = json.loads(r.text)
	except:
		data = {}
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
	try:
		with requests.get(url) as r:
			for item in json.loads(r.text):
				data.append({'x': item[1], 'y': item[2]})
	except:
		pass # Nothing to do if the call fails
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
	try:
		with requests.get(url) as h:
			for item in json.loads(h.text):
				dt = datetime.datetime.strptime(re.sub('\.[0-9]+', '', item[0]), "%Y-%m-%dT%H:%M:%S%z")
				time_diff = (dt - last_time).total_seconds()
				dist_diff = item[1] - last_dist
				speed = 0
				if time_diff > 0:
					speed = ((dist_diff / 1609.344) / (time_diff / 3600))
				data.append({'x': item[0], 'y': speed})
				last_time = dt
				last_dist = item[1]
	except:
		pass # Nothing to do if the call fails
	if len(data) > 0:
		return json.dumps(data)
	return ""

def getstopevents(dt, loc_manager=None):
	"""
	Queries the location manager for the times during a day when the user was stationary.

	:param dt: A Python date (or datetime) representing the day being queried.
	:param loc_manager: (Optional) The URL of an Imouto Location Manager server. If omitted, we use the LOCATION_MANAGER_URL setting.
	:return: A list containing a sequence of dicts containing the start and end times, as well as the average latitude and longitude.
	:rtype: list

	"""
	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address
	url = address + '/event/' + dt.strftime("%Y-%m-%d")
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = []

	return data

def getboundingbox(dts, dte, loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address
	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + '/bbox/' + id
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = [None, None, None, None]
	if data[0] is None:
		return []
	return data

def get_location_manager_import_queue(loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address
	url = address + '/import'
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = {"tasks": [], "sources": {}}
	return data

def get_location_manager_process_queue(loc_manager=None):

	address = settings.LOCATION_MANAGER_URL
	if not(loc_manager is None):
		address = loc_manager
	if not('://' in address):
		address = 'http://' + address
	url = address + '/process'
	try:
		r = requests.get(url)
		data = json.loads(r.text)
	except:
		data = {"tasks": [], "stats": {}}
	return data

def get_location_manager_report_queue(loc_manager=None):

	ret = []
	data = get_location_manager_process_queue(loc_manager)
	if 'tasks' in data:
		ret = ret + data['tasks']
	data = get_location_manager_import_queue(loc_manager)
	if 'tasks' in data:
		ret = ret + data['tasks']
	return ret

