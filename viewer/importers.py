import django, os, csv, socket, json, urllib, urllib.request, re, random, glob, sys, exifread, vobject, io, base64, imaplib, email, email.header, email.parser, email.message, requests
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
from dateutil import tz

from viewer.functions.monica import get_monica_contact_data, get_last_monica_activity, get_last_monica_call, assign_monica_avatar, create_monica_call, create_monica_activity_from_event
from viewer.functions.people import find_person_by_picasaid as find_person
from viewer.functions.geo import convert_to_degrees
from viewer.models import *
from viewer.tasks import precache_photo_thumbnail

def upload_file(temp_file, file_source, format=''):

	url = str(settings.LOCATION_MANAGER_URL).rstrip('/') + '/import'
	if format == '':
		r = requests.post(url, data={'file_source': file_source}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	else:
		r = requests.post(url, data={'file_source': file_source, 'file_format': format}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	if r.status_code == 200:
		return True
	return False

def export_monica_calls(from_date=None):

	dtsd = from_date
	now = datetime.datetime.now()
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []
	if from_date is None:
		dtsd = get_last_monica_call() + datetime.timedelta(days=1)
	dts = datetime.datetime(dtsd.year, dtsd.month, dtsd.day, 0, 0, 0, tzinfo=tz)
	dte = datetime.datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz) - datetime.timedelta(seconds=1)
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
	dts = datetime.datetime(dtsd.year, dtsd.month, dtsd.day, 0, 0, 0, tzinfo=tz)
	dte = datetime.datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz) - datetime.timedelta(seconds=1)
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
			prop = PersonProperty.objects.get(key=item[1], value=item[2])
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
			prop = PersonProperty.objects.get(key=item[1], value=num)
		except:
			prop = None
		if prop is None:
			try:
				prop = PersonProperty.objects.get('mobile', value=num)
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
			item['timestamp']['value'] = tz.localize(item['timestamp']['value'])
			item['timestamp']['value'] = item['timestamp']['value'].replace(tzinfo=pytz.utc) - item['timestamp']['value'].utcoffset() # I like everything in UTC. Bite me.
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

	for item in data:

		dts = item['date']
		dte = item['date'] + datetime.timedelta(seconds=item['length'])

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

def import_carddav(url, auth, countrycode='44'):

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
					with NamedTemporaryFile(mode='w', delete=False) as tf:
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
				url = settings.LOCATION_MANAGER_URL + '/position/' + ds
				r = urllib.request.urlopen(url)
				data = json.loads(r.read())
				if data['explicit'] == True:
					photo.lat = data['lat']
					photo.lon = data['lon']
					photo.save()

	return photo

def import_picasa_faces(picasafile):

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

def import_autographer_event_people(picasafile):

	contacts = {}
	faces = {}
	items = []
	path = os.path.dirname(picasafile)
	full_path = os.path.abspath(path)
	ret = []
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
		if not(filename.lower().endswith('.jpg')):
			continue
		parse = filename.lower().replace('.jpg', '').split('_')
		if len(parse) != 4:
			continue
		if not(parse[3].endswith('e')):
			continue
		parse[3] = parse[3][0:-1]
		if len(parse[2]) != 8:
			continue
		if len(parse[3]) != 6:
			continue
		dt = datetime.datetime(int(parse[2][0:4]), int(parse[2][4:6]), int(parse[2][6:8]), int(parse[3][0:2]), int(parse[3][2:4]), int(parse[3][4:6]), tzinfo=pytz.timezone(settings.TIME_ZONE))
		item = {'date': dt, 'people': [], 'events': []}
		for face in faces[filename]:
			person = find_person(face)
			if person is None:
				continue
			item['people'].append(person)
		for event in Event.objects.filter(start_time__lte=dt, end_time__gte=dt):
			item['events'].append(event)
		if len(item['people']) == 0:
			continue
		if len(item['events']) == 0:
			continue
		items.append(item)

	for item in items:
		for event in item['events']:
			for person in item['people']:
				event.people.add(person)
			if not(event in ret):
				ret.append(event)

	return ret

def import_photo_directory(path, tzinfo=pytz.UTC):

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

def import_calendar_feed(url):

	try:
		feed = CalendarFeed.objects.get(url=url)
	except:
		feed = CalendarFeed(url=url)
		feed.save()

	try:
		cal = Calendar(requests.get(url).text)
		events = list(cal.events)
	except:
		cal = None
		events = []

	if cal is None:
		return None

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

