import vobject, requests
from requests.auth import HTTPBasicAuth
from django.db.models import Q
from django.core.files import File
from tempfile import NamedTemporaryFile
from ics import Calendar

from viewer.models import Location, Person, PersonProperty, CalendarFeed, CalendarTask, CalendarAppointment

import logging
logger = logging.getLogger(__name__)

def import_carddav(url, auth, countrycode='44'):
	"""
	Imports CardDAV data from a web URL, and creates or augments Person objects accordingly.

	:param url: The URL from which to retrieve the CardDAV data.
	:param auth: The authentication (sent directly to the requests library) required to read the file, if necessary.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	"""
	r = requests.request("GET", url, auth=auth)
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
				if ptest.full_name == name:
					ct = ct + 1
					pobj = ptest
					continue
				if ptest.name == name:
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
					with NamedTemporaryFile(mode='wb') as tf:
						tf.write(person.contents['photo'][0].value.encode())
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
		try:
			data = str(event.serialize())
		except:
			data = ''
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
			try:
				item = CalendarAppointment.objects.get(eventid=id) # In case the item moves from one calendar to another
				item.calendar = feed
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
