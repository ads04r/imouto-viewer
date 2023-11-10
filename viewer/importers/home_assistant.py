import django, datetime, pytz, requests, json
from django.conf import settings
from dateutil.parser import parse as dateparse
from django.db.models import Q
from django.core.files import File
from django.core.cache import cache

from viewer.models import Event, Location, Person, DataReading

def import_home_assistant_readings(entity_id, reading_type, days=7):
	"""
	Imports data from a Home Assistant log directly into Imouto Viewer as DataReading objects. This
	function checks for existing data from a previous import, so the function may be called
	repeatedly without filling up the readings table with duplicated data. This function requires
	the settings HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN to be set.

	:param entity_id: The entity ID within Home Assistant whose data you would like to import (eg light.kitchen_light)
	:param reading_type: The reading type to be used within Imouto Viewer. This can be anything you like but should be unique to this entity.
	:param days: The number of days worth of data to import.
	:return: A list of the newly imported DataEntry objects, an empty list if nothing was done.
	:rtype: list
	"""
	dte = pytz.utc.localize(datetime.datetime.utcnow())
	dts = dte - datetime.timedelta(days=days)
	try:
		url = settings.HOME_ASSISTANT_URL.lstrip('/') + '/history/period/' + dts.strftime("%Y-%m-%d") + 'T' + dts.strftime("%H:%M:%S")
	except AttributeError:
		url = ''
	try:
		token = settings.HOME_ASSISTANT_TOKEN
	except AttributeError:
		token = ''
	ret = []
	if url == '':
		return ret
	if token == '':
		return ret
	if reading_type == '':
		return ret
	r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'filter_entity_id': entity_id, 'minimal_response': True, 'end_time': dte.strftime("%Y-%m-%d") + 'T' + dte.strftime("%H:%M:%S")})
	for item in json.loads(r.text):
		for subitem in item:
			try:
				state = int(subitem['state'])
			except:
				state = 0
			dt = dateparse(subitem['last_changed'])
			try:
				reading = DataReading.objects.get(start_time=dt, end_time=dt, type=reading_type)
			except:
				reading = DataReading(start_time=dt, end_time=dt, type=reading_type)
			reading.value = state
			reading.save()
			ret.append(reading)
	return ret

def import_home_assistant_events(entity_id, event_type, days=1):
	"""
	Imports data from a Home Assistant log directly into Imouto Viewer as Event objects. This
	function checks for existing data from a previous import, so the function may be called
	repeatedly without filling up the events table with duplicated data. This function requires
	the settings HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN to be set.

	:param entity_id: The entity ID within Home Assistant whose data you would like to import (eg light.kitchen_light)
	:param reading_type: The reading type to be used within Imouto Viewer. This can be anything you like but should be unique to this entity.
	:param days: The number of days worth of data to import.
	:return: A list of the newly imported Event objects, an empty list if nothing was done.
	:rtype: list
	"""
	dte = pytz.utc.localize(datetime.datetime.utcnow())
	dts = dte - datetime.timedelta(days=days)
	name = ''
	try:
		url = settings.HOME_ASSISTANT_URL.lstrip('/') + '/history/period/' + dts.strftime("%Y-%m-%d") + 'T' + dts.strftime("%H:%M:%S")
	except AttributeError:
		url = ''
	try:
		token = settings.HOME_ASSISTANT_TOKEN
	except AttributeError:
		token = ''
	data = []
	ret = []
	if url == '':
		return ret
	if token == '':
		return ret
	if event_type == '':
		return ret
	last_item = {'state': ''}
	r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'filter_entity_id': entity_id, 'minimal_response': True, 'end_time': dte.strftime("%Y-%m-%d") + 'T' + dte.strftime("%H:%M:%S")})
	for item in json.loads(r.text):
		for subitem in item:
			if not(isinstance(subitem, (dict))):
				continue
			if 'attributes' in subitem:
				if 'friendly_name' in subitem['attributes']:
					name = subitem['attributes']['friendly_name']
			if((last_item['state'] == 'on') & (subitem['state'] == 'off')):
				data.append({'from': dateparse(last_item['last_changed']), 'to': dateparse(subitem['last_changed'])})

			last_item = subitem
	if name == '':
		name = entity_id + ' event'
	for item in data:
		try:
			event = Event.objects.get(start_time=item['from'], end_time=item['to'], type=event_type)
		except:
			event = Event(start_time=item['from'], end_time=item['to'], type=event_type, caption=name)
			event.save()
		ret.append(event)
	return ret

def import_home_assistant_presence(uid, entity_id, days=7):
	"""
	Imports presence data from a Home Assistant log and augments Imouto Event objects with this accordingly. If a
	person has a 'presence' entity ID in Home Assistant and a Person entry in Imouto Viewer, this function can
	be used to map them together. It looks for all Events within the specified timespan (defaults to the last
	7 days) that take place at the user's home location, and adds the relevant person to each event.

	:param uid: The uid of the Person object in Imouto Viewer that corresponds to the relevant person.
	:param entity_id: The entity_id of the presence entity in Home Assistant that corresponds to the relevant person.
	:param days: The number of past days in which to search for presence events.
	:return: A list of the Event objects modified by the calling of the function. Empty list if there are none.
	:rtype: list
	"""
	dte = datetime.datetime.utcnow()
	dts = dte - datetime.timedelta(days=days)
	try:
		url = settings.HOME_ASSISTANT_URL.lstrip('/') + '/history/period/' + dts.strftime("%Y-%m-%d") + 'T' + dts.strftime("%H:%M:%S")
	except AttributeError:
		url = ''
	try:
		token = settings.HOME_ASSISTANT_TOKEN
	except AttributeError:
		token = ''
	try:
		home = Location.objects.get(id=settings.USER_HOME_LOCATION)
	except AttributeError:
		home = None
	person = Person.objects.get(uid=uid)
	data = []
	ret = []

	if url == '':
		return ret
	if token == '':
		return ret
	if home is None:
		return ret

	last_item = {'state': ''}
	r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'filter_entity_id': entity_id, 'minimal_response': True, 'end_time': dte.strftime("%Y-%m-%d") + 'T' + dte.strftime("%H:%M:%S")})
	for item in json.loads(r.text):
		for subitem in item:
			if not(isinstance(subitem, (dict))):
				continue
			if((last_item['state'] == 'home') & (subitem['state'] == 'not_home')):
				data.append({'from': dateparse(last_item['last_changed']), 'to': dateparse(subitem['last_changed'])})
			last_item = subitem
	for item in data:
		for event in Event.objects.filter(start_time__gte=item['from'], end_time__lte=item['to'], location=home):
			event.people.add(person)
			ret.append(event)

	return ret
