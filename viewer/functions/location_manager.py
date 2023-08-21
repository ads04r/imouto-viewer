import datetime, pytz, json, re, sys, os, requests
from django.conf import settings
from dateutil import parser

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
	r = requests.get(url)
	data = json.loads(r.text)

	ret = []

	for item in data:
		if item['timestart'] == item['timeend']:
			continue
		ret.append({'start_time': parser.parse(item['timestart']), 'end_time': parser.parse(item['timeend'])})

	return ret

