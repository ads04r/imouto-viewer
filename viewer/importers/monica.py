import django, datetime, pytz
from django.conf import settings
from django.db.models import Q
from django.core.files import File
from django.core.cache import cache
from tempfile import NamedTemporaryFile

from viewer.functions.monica import get_monica_contact_data, get_last_monica_activity, get_last_monica_call, assign_monica_avatar, create_monica_call, create_monica_activity_from_event
from viewer.models import Event, RemoteInteraction, PersonProperty

import logging
logger = logging.getLogger(__name__)

def export_monica_calls(from_date=None):
	dtsd = from_date
	now = datetime.datetime.now()
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []
	if from_date is None:
		dtsd = get_last_monica_call() + datetime.timedelta(days=1)
	dts = tz.localize(datetime.datetime(dtsd.year, dtsd.month, dtsd.day, 0, 0, 0))
	dte = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 0, 0)) - datetime.timedelta(seconds=1)
	ret = []

	for call in RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte).order_by('time'):
		if 'incoming call, rejected' in call.message:
			continue
		if 'missed call' in call.message:
			continue
		try:
			prop = PersonProperty.objects.get(value=call.address, key='phone')
		except:
			prop = None
		if prop is None:
			try:
				prop = PersonProperty.objects.get(value=call.address, key='mobile')
			except:
				prop = None
		if prop is None:
			try:
				prop = PersonProperty.objects.get(value=call.address, key='email')
			except:
				prop = None
		if prop is None:
			continue
		person = prop.person
		if person is None:
			continue
		if call.incoming:
			item = create_monica_call('Incoming call from ' + str(person), person, call.time, incoming=True)
		else:
			item = create_monica_call('Called ' + str(person), person, call.time, incoming=False)
		if item:
			ret.append(call)
	return ret

def export_monica_events(from_date=None):
	dtsd = from_date
	now = datetime.datetime.now()
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []
	if from_date is None:
		dtsd = get_last_monica_activity() + datetime.timedelta(days=1)
	dts = tz.localize(datetime.datetime(dtsd.year, dtsd.month, dtsd.day, 0, 0, 0))
	dte = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 0, 0)) - datetime.timedelta(seconds=1)
	ret = []
	for event in Event.objects.filter(start_time__gte=dts, start_time__lte=dte):
		if not((event.type == 'event') or (event.type == 'loc_prox')):
			continue
		if event.people.count() == 0:
			continue
		if create_monica_activity_from_event(event):
			ret.append(event)
	return ret

def export_monica_thumbnails():
	ret = []
	for prop in PersonProperty.objects.filter(key='monicahash'):
		person = prop.person
		hash = str(prop.value)
		with NamedTemporaryFile() as tempfile:
			try:
				img = person.thumbnail(size=300)
			except:
				img = None
			if not(img is None):
				img.save(tempfile.name, format='JPEG')
				if assign_monica_avatar(hash, tempfile.name, force=False):
					ret.append(person)
	return ret

def import_monica_contact_mappings(countrycode='44'):
	items = []
	ret = []
	for item in get_monica_contact_data():
		if not('contactFields' in item):
			continue
		for contact in item['contactFields']:
			items.append([contact['contact']['hash_id'], contact['contact_field_type']['type'], contact['content'].replace(' ', ''), contact['id']])
	for item in items:
		if item[1] != 'email':
			continue
		try:
			prop = PersonProperty.objects.get(key='email', value=item[2])
		except:
			prop = None
		if prop is None:
			continue
		if PersonProperty.objects.filter(person=prop.person, key='monicahash').count() > 0:
			continue
		newprop = PersonProperty(person=prop.person, key='monicahash', value=item[0])
		newprop.save()
		ret.append(newprop.person)
	for item in items:
		if item[1] != 'phone':
			continue
		num = item[2]
		if num.startswith('0'):
			num = '+' + countrycode + num[1:]
		try:
			prop = PersonProperty.objects.get(key='phone', value=num)
		except:
			prop = None
		if prop is None:
			try:
				prop = PersonProperty.objects.get(key='mobile', value=num)
			except:
				prop = None
		if prop is None:
			continue
		if PersonProperty.objects.filter(person=prop.person, key='monicahash').count() > 0:
			continue
		newprop = PersonProperty(person=prop.person, key='monicahash', value=item[0])
		newprop.save()
		ret.append(newprop.person)
	return ret
