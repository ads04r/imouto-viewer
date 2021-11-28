import django, os, csv, socket, json, urllib, urllib.request, re, random, glob, sys, exifread, vobject, io, base64, imaplib, email, email.header, email.parser, email.message
import datetime, pytz, pymysql, math
from django.conf import settings
from xml.dom import minidom
from fitparse import FitFile
from tzlocal import get_localzone
from xml.dom import minidom
from requests import request
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from PIL import Image
from dateutil.parser import parse as dateparse
from django.db.models import Q
from django.core.files import File
from tempfile import NamedTemporaryFile
from dateutil import tz

from viewer.models import *

def import_fit(parseable_fit_input):

	data = []
	fit = FitFile(parseable_fit_input)
	tz = get_localzone()
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
					print(" email " + email.value)
					pp = PersonProperty(person=pobj, key='email', value=email.value)
					pp.save()
			if 'tel' in person.contents:
				for phone in person.contents['tel']:
					num = phone.value.replace('-', '').replace(' ', '')
					if num.startswith('0'):
						num = '+' + countrycode + num[1:]
					phonestyle = 'phone'
					if num.startswith('+447'):
						phonestyle='mobile' # Very UK-centric.
					print(" " + phonestyle + " " + num)
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
						print(" email " + email.value)
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
						print(" " + phonestyle + " " + num)
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
