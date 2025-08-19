from django.conf import settings
from dateutil import parser
import datetime, pytz, json, re, requests

import logging
logger = logging.getLogger(__name__)

def get_logged_position(user, dt):
	"""
	Given a date, returns the point that the user was near at the time specified.

	:param date: A datetime.
	:return: A tuple (lat, lon) indicating the user's position
	:rtype: tuple(float)

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return (None, None)
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return (None, None)
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	ds = dt.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + '/position/' + ds
	try:
		with requests.get(url, headers={'Authorization': 'Token ' + bearer_token}) as r:
			data = json.loads(r.text)
	except:
		data = {}
	if(('lat' in data) & ('lon' in data)):
		return (data['lat'], data['lon'])

	return (None, None)

def get_possible_location_events(user, date, lat, lon):
	"""
	Given a date and a query point, returns a list of times the user was near the query point on the day specified.

	:param date: A date (not datetime).
	:param lat: The latitude of the query point.
	:param lon: The longitude of the query point.
	:return: A list of dictionaries containing start_time and end_time of potential events.
	:rtype: list[dict]

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return []
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return []
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']

	ds = date.strftime("%Y-%m-%d")
	url = address + '/event/' + ds + '/' + str(lat) + '/' + str(lon)
	try:
		with requests.get(url, headers={'Authorization': 'Token ' + bearer_token}) as r:
			data = json.loads(r.text)
	except:
		data = []

	ret = []

	for item in data:
		if item['timestart'] == item['timeend']:
			continue
		ret.append({'start_time': parser.parse(item['timestart']), 'end_time': parser.parse(item['timeend'])})

	return ret

def getgeoline(user, dts, dte):
	"""
	Queries the location manager for the user's route between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:return: The raw output from the location manager, which should be a dict containing GeoJSON polyline, among other things.
	:rtype: dict

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return ""
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return ""
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/route/" + id + "?format=json"
	data = {}
	try:
		with requests.get(url, headers={'Authorization': 'Token ' + bearer_token}) as r:
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

def getelevation(user, dts, dte):
	"""
	Queries the location manager for the user's elevation between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:return: A list containing a sequence of two-element {x, y} dicts, useful for drawing an elevation graph.
	:rtype: list

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return ""
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return ""
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/elevation/" + id + "?format=json"
	data = []
	try:
		with requests.get(url, headers={'Authorization': 'Token ' + bearer_token}) as r:
			for item in json.loads(r.text):
				data.append({'x': item[1], 'y': item[2]})
	except:
		pass # Nothing to do if the call fails
	if len(data) > 0:
		return json.dumps(data)
	return ""

def getspeed(user, dts, dte):
	"""
	Queries the location manager for the user's speed between two times.

	:param dts: A Python datetime representing the start of the time period being queried.
	:param dte: A Python datetime representing the end of the time period being queried.
	:return: A list containing a sequence of two-element {x, y} dicts, useful for drawing a graph with speed on the y-axis and time on the x-axis.
	:rtype: list

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return '[]'
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return '[]'

	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']

	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + "/elevation/" + id + "?format=json"
	data = []
	last_dist = 0
	last_time = dts
	try:
		with requests.get(url, headers={'Authorization': 'Token ' + bearer_token}) as h:
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

def getstopevents(user, dt):
	"""
	Queries the location manager for the times during a day when the user was stationary.

	:param dt: A Python date (or datetime) representing the day being queried.
	:return: A list containing a sequence of dicts containing the start and end times, as well as the average latitude and longitude.
	:rtype: list

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return []
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return []

	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address + '/event/' + dt.strftime("%Y-%m-%d")
	try:
		r = requests.get(url, headers={'Authorization': 'Token ' + bearer_token})
		data = json.loads(r.text)
	except:
		data = []

	return data

def getamenities(user, dt):
	"""
	Queries the location manager for the amenities the user was near on the specified date.

	:param dt: A Python date (or datetime) representing the day being queried.
	:return: A list of dicts representing the amenities.
	:rtype: list

	"""
	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return []
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return []

	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address + '/event/' + dt.strftime("%Y-%m-%d")
	try:
		r = requests.get(url, headers={'Authorization': 'Token ' + bearer_token})
		data = json.loads(r.text)
	except:
		data = []

	ret = []
	for item in data:
		if not 'amenities' in item:
			continue
		for place in item['amenities']:
			if not place in ret:
				ret.append(place)
	return ret

def getboundingbox(user, dts, dte):

	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return []
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return []

	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
	url = address + '/bbox/' + id
	try:
		r = requests.get(url, headers={'Authorization': 'Token ' + bearer_token})
		data = json.loads(r.text)
	except:
		data = [None, None, None, None]
	if data[0] is None:
		return []
	return data

def get_location_manager_import_queue(user):

	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return {"tasks": [], "stats": {}}
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return {"tasks": [], "stats": {}}
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address + '/import'
	try:
		r = requests.get(url, headers={'Authorization': 'Token ' + bearer_token})
		data = json.loads(r.text)
	except:
		data = {"tasks": [], "sources": {}}
	return data

def get_location_manager_process_queue(user):

	if not 'LOCATION_MANAGER_URL' in user.profile.settings:
		return {"tasks": [], "stats": {}}
	if not 'LOCATION_MANAGER_TOKEN' in user.profile.settings:
		return {"tasks": [], "stats": {}}
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address + '/process'
	try:
		r = requests.get(url, headers={'Authorization': 'Token ' + bearer_token})
		data = json.loads(r.text)
	except:
		data = {"tasks": [], "stats": {}}
	return data

def get_location_manager_report_queue(user):

	ret = []
	data = get_location_manager_process_queue(user)
	if 'tasks' in data:
		ret = ret + data['tasks']
	data = get_location_manager_import_queue(user)
	if 'tasks' in data:
		ret = ret + data['tasks']
	return ret

def upload_csv_data(user, data, source):

	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address + '/import'

	files = {'uploaded_file': data}
	data = {'file_source': source, 'file_format': 'csv'}

	requests.post(url, headers={'Authorization': 'Token ' + bearer_token}, files=files, data=data)

