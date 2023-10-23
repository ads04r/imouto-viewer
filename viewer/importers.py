import django, os, csv, socket, json, re, random, glob, sys, exifread, vobject, io, base64, imaplib, email, email.header, email.parser, email.message, requests
import datetime, pytz, pymysql, math
from django.conf import settings
from xml.dom import minidom
from fitparse import FitFile
from xml.dom import minidom
from requests import request
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from PIL import Image
from dateutil.parser import parse as dateparse
from django.db.models import Q
from django.core.files import File
from django.core.cache import cache
from tempfile import NamedTemporaryFile
from ics import Calendar

from viewer.functions.monica import get_monica_contact_data, get_last_monica_activity, get_last_monica_call, assign_monica_avatar, create_monica_call, create_monica_activity_from_event
from viewer.functions.people import find_person_by_picasaid as find_person
from viewer.functions.geo import convert_to_degrees
from viewer.functions.git import get_recent_github_commits, get_recent_gitea_commits
from viewer.models import *
from viewer.tasks import precache_photo_thumbnail, generate_location_events

def import_github_history(since=None):
	"""
	Calls the public Github API to determine a list of commits pushed by the user, and imports these
	as GitCommit objects.

	:return: A list of the new GitCommit objects that have been added.
	:rtype: list(GitCommit)
	"""
	try:
		username = settings.USER_GITHUB
	except AttributeError:
		username = None
	if username is None:
		return []
	if since is None:
		last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	else:
		last_commit = since
	ret = []
	for commit in get_recent_github_commits(username, since=last_commit):
		if commit['time'] <= last_commit:
			continue
		try:
			item = GitCommit(hash=commit['hash'], comment=commit['comment'], repo_url=commit['repo_url'], commit_date=commit['time'], additions=commit['stats']['additions'], deletions=commit['stats']['deletions'])
			item.save()
		except:
			item = None
		if item is None:
			continue
		ret.append(item)
	return ret

def import_gitea_history(since=None):
	"""
	Calls a Gitea API to determine a list of commits pushed by the user, and imports these
	as GitCommit objects.

	:return: A list of the new GitCommit objects that have been added.
	:rtype: list(GitCommit)
	"""
	try:
		username = settings.GITEA_USER
	except AttributeError:
		username = None
	try:
		token = settings.GITEA_TOKEN
	except AttributeError:
		token = None
	try:
		url = settings.GITEA_URL
	except AttributeError:
		url = None
	if username is None:
		return []
	if url is None:
		return []
	if token is None:
		return []

	if since is None:
		last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	else:
		last_commit = since
	ret = []
	for commit in get_recent_gitea_commits(username, token, url, since=last_commit):
		if commit['time'] <= last_commit:
			continue
		try:
			item = GitCommit(hash=commit['hash'], comment=commit['comment'], repo_url=commit['repo_url'], commit_date=commit['time'], additions=None, deletions=None)
			item.save()
		except:
			item = None
		if item is None:
			continue
		ret.append(item)
	return ret

def upload_file(temp_file, file_source, format=''):
	"""
	Uploads a file to the configured location manager. When calling this function you need to pass a string
	representing the source of the data (eg 'handheld_gps', 'fitness_tracker', 'phone').

	:param temp_file: The path of the file being sent.
	:param file_source: A string representing the source of the data.
	:param format: Currently unused.
	:return: True if the upload was successful, False if not.
	:rtype: bool
	"""
	url = str(settings.LOCATION_MANAGER_URL).rstrip('/') + '/import'
	if format == '':
		r = requests.post(url, data={'file_source': file_source}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	else:
		r = requests.post(url, data={'file_source': file_source, 'file_format': format}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	if r.status_code == 200:
		generate_location_events()
		return True
	return False

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
	data = []
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
	dte = datetime.datetime.utcnow()
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

def import_fit(parseable_fit_input):
	"""
	Reads data in ANT-FIT format, typically used by Garmin fitness trackers, and generates DataValues based on the information contained within.

	:param parseable_fit_input: A path to an ANT-FIT file.
	"""
	data = []
	fit = FitFile(parseable_fit_input)
	tz = pytz.UTC
	for record in fit.get_messages('record'):
		item = {}
		for recitem in record:
			k = recitem.name
			if ((k != 'heart_rate') & (k != 'timestamp') & (k != 'cadence')):
				continue
			v = {}
			v['value'] = recitem.value
			v['units'] = recitem.units
			if ((v['units'] == 'semicircles') & (not(v['value'] is None))):
				v['value'] = float(v['value']) * ( 180 / math.pow(2, 31) )
				v['units'] = 'degrees'
			item[k] = v
		if item['timestamp']['value'].tzinfo is None or item['timestamp']['value'].utcoffset(item['timestamp']['value']) is None:
			item['timestamp']['value'] = pytz.utc.localize(item['timestamp']['value']) # If no timestamp, we assume UTC
		newitem = {}
		newitem['date'] = item['timestamp']['value']
		if 'heart_rate' in item:
			newitem['heart'] = item['heart_rate']['value']
		if 'cadence' in item:
			if item['cadence']['value'] > 0:
				newitem['cadence'] = item['cadence']['value']
		newitem['length'] = 1
		if len(data) > 0:
			lastitem = data[-1]
			lastitem['length'] = int((newitem['date'] - lastitem['date']).total_seconds())
			data[-1] = lastitem
		data.append(newitem)

	days = []
	for item in data:

		dts = item['date']
		dte = item['date'] + datetime.timedelta(seconds=item['length'])
		dtsd = dts.date()
		dted = dte.date()
		if not(dtsd in days):
			days.append(dtsd)
		if not(dted in days):
			days.append(dted)

		if 'heart' in item:
			if not(item['heart'] is None):
				try:
					event = DataReading.objects.get(start_time=dts, end_time=dte, type='heart-rate')
				except:
					event = DataReading(start_time=dts, end_time=dte, type='heart-rate', value=item['heart'])
					event.save()

		if 'cadence' in item:
			if not(item['cadence'] is None):
				try:
					event = DataReading.objects.get(start_time=dts, end_time=dte, type='cadence')
				except:
					event = DataReading(start_time=dts, end_time=dte, type='cadence', value=item['cadence'])
					event.save()

	for dt in days:
		Day.objects.filter(date=dt).delete()

def import_carddav(url, auth, countrycode='44'):
	"""
	Imports CardDAV data from a web URL, and creates or augments Person objects accordingly.

	:param url: The URL from which to retrieve the CardDAV data.
	:param auth: The authentication (sent directly to the requests library) required to read the file, if necessary.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	"""
	r = request("GET", url, auth=auth)
	cards = r.text.split('BEGIN:VCARD')
	people = []
	for s in cards:
		if s == '':
			continue
		vcard = vobject.readOne('BEGIN:VCARD' + s)
		people.append(vcard)

	for person in people:

		pobj = None
		name = person.fn.value

		if 'email' in person.contents:
			for email in person.contents['email']:
				try:
					pp = PersonProperty.objects.get(key='email', value=str(email.value))
				except:
					pp = None
				if not(pp is None):
					pobj = pp.person
		if 'tel' in person.contents:
			for phone in person.contents['tel']:
				try:
					pp = PersonProperty.objects.get(Q(value=str(phone.value)), Q(key='phone') | Q(key='mobile'))
				except:
					pp = None
				if not(pp is None):
					pobj = pp.person

		if pobj is None:
			ct = 0
			for ptest in Person.objects.all():
				if ptest.full_name() == name:
					ct = ct + 1
					pobj = ptest
					continue
				if ptest.name() == name:
					ct = ct + 1
					pobj = ptest
					continue
			if ct > 1:
				pobj = None

		if pobj is None:

			try:
				given_name = str(person.n.value.given).strip()
				family_name = str(person.n.value.family).strip()
			except:
				given_name = name
				family_name = ''

			id = name.replace(' ', '').replace("'", '').replace('-', '').replace('.', '').lower()
			if id == 'yggdrasil':
				continue
			if id == 'breakdowncover':
				continue
			pobj = Person(uid=id, given_name=given_name, family_name=family_name)
			pobj.save()

			if 'email' in person.contents:
				for email in person.contents['email']:
					pp = PersonProperty(person=pobj, key='email', value=email.value)
					pp.save()
			if 'tel' in person.contents:
				for phone in person.contents['tel']:
					num = phone.value.replace('-', '').replace(' ', '')
					if num.startswith('0'):
						num = '+' + countrycode + num[1:]
					phonestyle = 'phone'
					if ((countrycode == '44') & (num.startswith('+447'))):
						phonestyle='mobile' # Very UK-centric.
					pp = PersonProperty(person=pobj, key=phonestyle, value=num)
					pp.save()

			pobj.save()

		else:

			if not(pobj.image):
				if 'photo' in person.contents:
					with NamedTemporaryFile(mode='wb', delete=False) as tf:
						tf.write(person.contents['photo'][0].value)
						pobj.image.save('/' + str(pobj.uid) + '.jpg', File(open(tf.name, 'rb')))
						pobj.save()

			if 'email' in person.contents:
				for email in person.contents['email']:
					try:
						pp = PersonProperty.objects.get(person=pobj, key='email', value=email.value)
					except:
						pp = PersonProperty(person=pobj, key='email', value=email.value)
						pp.save()
			if 'tel' in person.contents:
				for phone in person.contents['tel']:
					num = phone.value.replace('-', '').replace(' ', '')
					if num.startswith('0'):
						num = '+' + countrycode + num[1:]
					phonestyle = 'phone'
					if num.startswith('+447'):
						phonestyle='mobile'
					try:
						pp = PersonProperty.objects.get(person=pobj, key=phonestyle, value=num)
					except:
						pp = PersonProperty(person=pobj, key=phonestyle, value=num)
						pp.save()

def import_sms_from_imap(host, username, password, inbox='INBOX', countrycode='44'):
	"""
	For users using the Android app 'SMS Backup+', this function gets the user's text messages that have been stored on
	an IMAP mail server by the app and imports them into Imouto Viewer as RemoteInteraction objects.

	:param host: The host name or IP address of the IMAP server.
	:param username: The username needed to log into the IMAP server.
	:param password: The password needed to log into the IMAP server.
	:param inbox: The name of the inbox in which to search for new messages.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	:return: The number of new messages imported.
	:rtype: int
	"""
	minmsg = RemoteInteraction.objects.filter(type='sms').order_by('-time')[0]
	mindt = minmsg.time
	minds = mindt.strftime("%-d-%b-%Y")

	acc = imaplib.IMAP4_SSL(host)
	try:
		rv, data = acc.login(username, password);
	except imaplib.IMAP4.error:
		return -1

	rv, mailboxes = acc.list()
	rv, data = acc.select(inbox)
	rv, data = acc.search(None, '(SINCE "' + minds + '")')

	ct = 0

	if rv == 'OK':

		for i in data[0].split():
			rv, data = acc.fetch(i, '(RFC822)')
			if rv != 'OK':
				continue
			msg = email.message_from_string(data[0][1].decode('utf-8'))
			decode = email.header.decode_header(msg['Subject'])[0]
			subject = decode[0]
			dtpl = email.utils.parsedate_tz(msg['Date'])
			dt = datetime.datetime(*dtpl[0:6], tzinfo=tz.tzoffset('FLT', dtpl[9]))
			ds = dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
			body = msg.get_payload()
			if((type(body)) is list):
				body = body[0]
			if isinstance(body, email.message.Message):
				body = body.get_payload()

			if dt < mindt:
				continue

			body = body.replace('=2E', '.').replace('=\r\n', '')
			parser = email.parser.HeaderParser()
			headers = parser.parsestr(msg.as_string())
			msgtype = headers['X-smssync-datatype']

			if msgtype != 'SMS':
				continue

			number = str(headers['X-smssync-address']).replace(' ', '')
			if number[0] == '0':
				number = '+' + countrycode + number[1:]
			smstype = int(headers['X-smssync-type'])
			if smstype == 1:
				incoming = True
			else:
				incoming = False

			try:
				msg = RemoteInteraction.objects.get(type='sms', time=dt, address=number, incoming=incoming, title='', message=body)
			except:
				msg = RemoteInteraction(type='sms', time=dt, address=number, incoming=incoming, title='', message=body)
				ct = ct + 1
				msg.save()

	return ct

def import_calls_from_imap(host, username, password, inbox='INBOX', countrycode='44'):
	"""
	For users using the Android app 'SMS Backup+', this function gets the user's phone call history that has been stored on
	an IMAP mail server by the app and imports them into Imouto Viewer as RemoteInteraction objects.

	:param host: The host name or IP address of the IMAP server.
	:param username: The username needed to log into the IMAP server.
	:param password: The password needed to log into the IMAP server.
	:param inbox: The name of the inbox in which to search for new messages.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	:return: The number of new messages imported.
	:rtype: int
	"""
	try:
		minmsg = RemoteInteraction.objects.filter(type='phone-call').order_by('-time')[0]
	except:
		minmsg = RemoteInteraction.objects.order_by('time')[0]
	mindt = minmsg.time
	minds = mindt.strftime("%-d-%b-%Y")

	acc = imaplib.IMAP4_SSL(host)
	try:
		rv, data = acc.login(username, password);
	except imaplib.IMAP4.error:
		return -1

	rv, mailboxes = acc.list()
	rv, data = acc.select('"' + inbox + '"')
	rv, data = acc.search(None, '(SINCE "' + minds + '")')

	ct = 0

	if rv == 'OK':

		for i in data[0].split():
			rv, data = acc.fetch(i, '(RFC822)')
			if rv != 'OK':
				continue
			msg = email.message_from_string(data[0][1].decode('utf-8'))
			decode = email.header.decode_header(msg['Subject'])[0]
			subject = decode[0]
			dtpl = email.utils.parsedate_tz(msg['Date'])
			dt = datetime.datetime(*dtpl[0:6], tzinfo=tz.tzoffset('FLT', dtpl[9]))
			ds = dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
			body = msg.get_payload()
			if((type(body)) is list):
				body = body[0]
			if isinstance(body, email.message.Message):
				body = body.get_payload()

			if dt < mindt:
				continue

			body = body.replace('=2E', '.').replace('=\r\n', '')
			parser = email.parser.HeaderParser()
			headers = parser.parsestr(msg.as_string())
			msgtype = headers['X-smssync-datatype']

			if msgtype != 'CALLLOG':
				continue

			number = str(headers['X-smssync-address']).replace(' ', '')
			if len(number) == 0:
				continue
			if number[0] == '0':
				number = '+' + countrycode + number[1:]
			if body.endswith('(outgoing call)'):
				incoming = False
			else:
				incoming = True

			try:
				msg = RemoteInteraction.objects.get(type='phone-call', time=dt, address=number, incoming=incoming, title='', message=body)
			except:
				msg = RemoteInteraction(type='phone-call', time=dt, address=number, incoming=incoming, title='', message=body)
				msg.save()
				ct = ct + 1
				msg.save()

	return ct

def __parse_scale_csv(filepath):

	headers = []
	ret = []
	with open(filepath) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		for row in csv_reader:
			if len(headers) == 0:
				headers = row
				continue
			i = len(headers)
			j = len(row)
			if i < j:
				j = i
			item = {}
			for i in range(0, j):
				item[headers[i]] = row[i]
			ret.append(item)
	return(ret)

def import_openscale(filepath):
	"""
	For users of the Android app OpenScale, this function takes a file exported by the app and
	imports it into the Imouto Viewer database as DataReading objects for weight, fat percentage,
	muscle percentage and water readings.

	:param filepath: The path of the file to be imported.
	:return: A list of lists representing the data that has been imported.
	:rtype: list
	"""
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []

	data = __parse_scale_csv(filepath)
	for item in data:
		ds = item['dateTime']
		try:
			dt = tz.localize(datetime.datetime.strptime(ds, "%Y-%m-%d %H:%M"))
		except:
			dt = tz.localize(datetime.datetime.strptime(ds, "%d.%m.%Y %H:%M"))

		try:
			weight = DataReading.objects.get(start_time=dt, end_time=dt, type='weight')
		except:
			value = (float(item['weight']) * 1000) + 0.5
			if value > 87000:
				weight = DataReading(start_time=dt, end_time=dt, type='weight', value=int(value))
				ret.append([str(dt), 'weight', str(float(weight.value) / 1000)])
				weight.save()

		try:
			fat = DataReading.objects.get(start_time=dt, end_time=dt, type='fat')
		except:
			value = float(item['fat']) + 0.5
			if value > 10:
				fat = DataReading(start_time=dt, end_time=dt, type='fat', value=int(value))
				ret.append([str(dt), 'fat', str(fat.value) + "%"])
				fat.save()

		try:
			muscle = DataReading.objects.get(start_time=dt, end_time=dt, type='muscle')
		except:
			value = float(item['muscle']) + 0.5
			if value > 10:
				muscle = DataReading(start_time=dt, end_time=dt, type='muscle', value=int(value))
				ret.append([str(dt), 'muscle', str(muscle.value) + "%"])
				muscle.save()

		try:
			water = DataReading.objects.get(start_time=dt, end_time=dt, type='water')
		except:
			value = float(item['water']) + 0.5
			if value > 10:
				water = DataReading(start_time=dt, end_time=dt, type='water', value=int(value))
				ret.append([str(dt), 'water', str(water.value) + "%"])
				water.save()
	return ret

def import_photo_file(filepath, tzinfo=pytz.UTC):
	"""
	Imports a photo into the lifelog data as a Photo object. During import, the function attempts to
	annotate the photo based on EXIF data, and existing data within Imouto if available.

	:param filepath: The path of the photo to import.
	:param tzinfo: A pytz timezone object relating to the timezone in which the photo was taken, as older cameras (such as mine!) don't store this information.
	:return: Returns the new Photo object created by the function call.
	:rtype: Photo
	"""
	path = os.path.abspath(filepath)

	try:
		photo = Photo.objects.get(file=path)
	except:
		photo = Photo(file=path)
		photo.save()

	exif = exifread.process_file(open(path, 'rb'))

	if 'Image DateTime' in exif:
		dsa = str(exif['Image DateTime']).replace(' ', ':').split(':')
		try:
			dt = tzinfo.localize(datetime.datetime(int(dsa[0]), int(dsa[1]), int(dsa[2]), int(dsa[3]), int(dsa[4]), int(dsa[5])))
		except:
			dt = tzinfo.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(path)))
		photo.time = dt.astimezone(pytz.UTC)
		photo.save()

	if 'EXIF DateTimeOriginal' in exif:
		dsa = str(exif['EXIF DateTimeOriginal']).replace(' ', ':').split(':')
		try:
			dt = tzinfo.localize(datetime.datetime(int(dsa[0]), int(dsa[1]), int(dsa[2]), int(dsa[3]), int(dsa[4]), int(dsa[5])))
		except:
			dt = tzinfo.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(path)))
		photo.time = dt.astimezone(pytz.UTC)
		photo.save()

	if (('GPS GPSLatitude' in exif) & ('GPS GPSLongitude' in exif)):
		latdms = exif['GPS GPSLatitude']
		londms = exif['GPS GPSLongitude']
		latr = str(exif['GPS GPSLatitudeRef']).lower()
		lonr = str(exif['GPS GPSLongitudeRef']).lower()
		lat = convert_to_degrees(latdms)
		if latr == 's':
			lat = 0 - lat
		lon = convert_to_degrees(londms)
		if lonr == 'w':
			lon = 0 - lon
		if((lat != 0.0) or (lon != 0.0)):
			photo.lat = lat
			photo.lon = lon
			photo.save()
	else:
		if photo:
			if photo.time:
				ds = photo.time.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
				try:
					url = settings.LOCATION_MANAGER_URL + '/position/' + ds
					r = requests.get(url)
					data = json.loads(r.text)
				except:
					data = {'explicit': False}
				if data['explicit'] == True:
					photo.lat = data['lat']
					photo.lon = data['lon']
					photo.save()

	return photo

def import_picasa_faces(picasafile):
	"""
	Tags the photos within Imouto Viewer with person data from Google Picasa. Takes a Picasa sidecar file,
	attempts to match it up with photos and people already in Imouto Viewer, and links them accordingly.

	:param picasafile: The path of the Picasa sidecar file from which to read.
	:return: The number of new tags created.
	:rtype: int
	"""
	contacts = {}
	faces = {}
	path = os.path.dirname(picasafile)
	full_path = os.path.abspath(path)
	ret = 0
	if os.path.exists(picasafile):
		lf = ''
		with open(picasafile) as f:
			lines = f.readlines()
		for liner in lines:
			line = liner.strip()
			if line == '':
				continue
			if ((line[0] == '[') & (line[-1:] == ']')):
				lf = line.lstrip('[').rstrip(']')
			if lf == 'Contacts2':
				parse = line.replace(';', '').split('=')
				if len(parse) == 2:
					contacts[parse[0]] = find_person(parse[0], parse[1])
			if ((line[0:6] == 'faces=') & (lf != '')):
				item = []
				for segment in line[6:].split(';'):
					structure = segment.split(',')
					if not(lf in faces):
						faces[lf] = []
					faces[lf].append(structure[1])

	for filename in faces.keys():
		if len(filename) == 0:
			continue
		full_filename = os.path.join(full_path, filename)
		if not(os.path.isfile(full_filename)):
			continue
		try:
			photo = Photo.objects.get(file=full_filename)
		except:
			photo = None
		if photo is None:
			continue
		for file_face in faces[filename]:
			if not(file_face in contacts):
				contacts[file_face] = find_person(file_face)
			person = contacts[file_face]
			if person is None:
				continue
			if person in photo.people.all():
				continue
			photo.people.add(person)
			ret = ret + 1
			for event in photo.events().all():
				event.people.add(person)
	return ret

def import_photo_directory(path, tzinfo=pytz.UTC):
	"""
	Scans a local directory for photos and calls import_photo_file for every photo file found. If it
	finds a Picasa sidecar file, it imports that too by calling import_picasa_faces.

	:param filepath: The path of the directory to scan.
	:param tzinfo: A pytz timezone object relating to the timezone in which the photos were taken, as older cameras (such as mine!) don't store this information.
	:return: A list of the new Photo objects created with this function call.
	:rtype: list
	"""
	full_path = os.path.abspath(path)
	ret = []

	picasafile = os.path.join(full_path, '.picasa.ini')
	if(not(os.path.exists(picasafile))):
		picasafile = os.path.join(full_path, 'picasa.ini')
	if(not(os.path.exists(picasafile))):
		picasafile = os.path.join(full_path, 'Picasa.ini')

	photos = []
	for f in os.listdir(full_path):
		if not(f.lower().endswith('.jpg')):
			continue
		photo_file = os.path.join(full_path, f)
		try:
			photo = Photo.objects.get(file=photo_file)
		except:
			photo = None
			photos.append(photo_file)

	for photo in photos:
		p = import_photo_file(photo, tzinfo)
		if p is None:
			continue
		precache_photo_thumbnail(p.id)
		ret.append(photo)

	faces = import_picasa_faces(picasafile)

	gps_data = []
	for photo_path in ret:
		try:
			photo = Photo.objects.get(file=photo_path)
		except:
			photo is None
		if not(photo is None):
			if photo.time:
				if photo.lat:
					if photo.lon:
						ds = photo.time.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
						lat = str(photo.lat)
						lon = str(photo.lon)
						gps_data.append([ds, lat, lon])
	if len(gps_data) > 0:
		op = ''
		for row in gps_data:
			op = op + '\t'.join(row) + '\n'

		url = settings.LOCATION_MANAGER_URL + '/import'
		files = {'uploaded_file': op}
		data = {'file_source': 'photo', 'file_format': 'csv'}

		r = requests.post(url, files=files, data=data)
		st = r.status_code

	return ret

def import_calendar_feed(url, username=None, password=None):
	"""
	Imports CalDAV data from a web URL, and creates or augments CalendarFeed, CalendarAppointment and CalendarTask objects accordingly.

	:param url: The URL from which to retrieve the CardDAV data.
	:param username: The username, if the URL is a WebDav resource.
	:param password: The password, if the URL is a WebDav resource.
	:return: A list of new CalendarAppointment objects created by this function call.
	:rtype: list
	"""
	try:
		feed = CalendarFeed.objects.get(url=url)
	except:
		feed = CalendarFeed(url=url)
		feed.save()

	try:
		if username is None:
			ics_text = requests.get(url).text
		else:
			ics_text = requests.get(url, auth=HTTPBasicAuth(username, password)).text
		cal = Calendar(ics_text)
		events = list(cal.events)
	except:
		cal = None
		events = []

	if cal is None:
		return None

	for task in list(cal.todos):

		completed = None
		due = None
		created = None
		if task.completed:
			completed = task.completed.datetime
		if task.due:
			due = task.due.datetime
		if task.created:
			created = task.created.datetime
		label = ''
		if task.name:
			label = task.name
		description = ''
		if task.description:
			description = task.description
		data = str(task.serialize())
		id = str(task.uid)

		try:
			item = CalendarTask.objects.get(taskid=id, calendar=feed)
		except:
			item = CalendarTask(taskid=id, calendar=feed)

		item.time_created = created
		item.time_due = due
		item.time_completed = completed
		item.data = data
		item.caption = label
		item.description = description

		item.save()

	ret = []

	for event in events:

		id = str(event.uid)

		label = str(event.name)
		description = str(event.description)
		data = str(event.serialize())
		location = str(event.location)
		try:
			loc = Location.objects.get(label__icontains=location)
		except:
			loc = None

		start_time = event.begin.datetime
		end_time = None
		if event.has_end():
			end_time = event.end.datetime
		all_day = event.all_day

		try:
			item = CalendarAppointment.objects.get(eventid=id, calendar=feed)
		except:
			item = CalendarAppointment(eventid=id, calendar=feed)
			ret.append(item)

		item.start_time = start_time
		item.end_time = end_time
		item.all_day = all_day
		item.data = data
		item.caption = label
		item.description = description
		if not(loc is None):
			item.location = loc

		item.save()

	return ret

def import_data(data):
	"""
	Import generic sensor data into Imouto's database.

	:param data: A list of dicts. The dicts must all contain the keys start_time, end_time, type and value.
	:return: A three-item tuple representing the number of new records inserter, the number of records updated, and the number of records that could not be imported, in that order.
	:rtype: tuple
	"""
	done = 0
	updated = 0
	inserted = 0
	for item in data:
		done = done + 1
		try:
			e = DataReading.objects.get(start_time=item['start_time'], end_time=item['end_time'], type=item['type'])
			e.value = item['value']
			e.save()
			updated = updated + 1
		except:
			e = DataReading(start_time=item['start_time'], end_time=item['end_time'], type=item['type'], value=item['value'])
			e.save()
			inserted = inserted + 1

	return (inserted, updated, (len(data) - done))
