import datetime, pytz, json, psutil
from django.db.models import Sum, Count
from django.conf import settings

from viewer.models import create_or_get_day, LifePeriod, RemoteInteraction, Photo, Location, Person, PersonProperty, DataReading, Event, EventTag, EventWorkoutCategory, CalendarTask

import logging
logger = logging.getLogger(__name__)

def __display_timeline_event(event):

	if event.type == 'life_event':
		return False
	if event.description == '':
		if event.type == 'loc_prox':
			if event.location is None:
				return False
			if event.location.label == 'Home':
				if event.photos().count() == 0:
					return False
		if event.type == 'journey':
			ddt = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=7)
			if event.end_time < ddt:
				if event.people.all().count() == 0:
					if event.photos().count() == 0:
						if (float(event.distance()) < 1):
							return False
	return True

def first_event_time(user):

	try:
		return Event.objects.filter(user=user).order_by('start_time').first().start_time
	except:
		return None

def generate_life_grid(user, start_date, weeks):

	life = []
	year = []
	year_birthday = user.profile.date_of_birth
	for i in range(0, weeks):
		dts = start_date + datetime.timedelta(days=(7 * i))
		dte = dts + datetime.timedelta(days=6)
		if ((dts <= year_birthday) & (year_birthday <= dte)):
			year_birthday = year_birthday.replace(year=year_birthday.year + 1)
			if len(year) > 0:
				life.append(year)
				year = []
		dtts = pytz.utc.localize(datetime.datetime(dts.year, dts.month, dts.day, 0, 0, 0))
		dtte = pytz.utc.localize(datetime.datetime(dte.year, dte.month, dte.day, 23, 59, 59))
		item = {'start_time': dts, 'end_time': dte, 'events': Event.objects.filter(user=user, type='life_event', start_time__lte=dtte, end_time__gte=dtts), 'periods': LifePeriod.objects.filter(user=user, start_time__lte=dtte, end_time__gte=dtts)}
		year.append(item)
	if len(year) > 0:
		life.append(year)
	return life

def get_report_queue():

	ret = []

	return ret

def get_timeline_events(user, dt):

	dtq = dt
	events = []
	while len(events) == 0:
		for event in Event.objects.filter(user=user, start_time__gte=dtq, start_time__lt=(dtq + datetime.timedelta(hours=24))).order_by('-start_time'):
			if __display_timeline_event(event):
				events.append(event)
		dtq = dtq - datetime.timedelta(hours=24)
	return events

def get_today(user):

	dt = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(settings.TIME_ZONE)).date()
	return create_or_get_day(user, dt)

def imouto_json_serializer(data):
	if isinstance(data, datetime.datetime):
		return data.strftime("%Y-%m-%d %H:%M:%S %Z")
	if isinstance(data, (Person, Location, Event)):
		return data.to_dict()

def unixtime_to_datetime(unixtime):
	return (pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0)) + datetime.timedelta(seconds=int(unixtime))).astimezone(pytz.timezone(settings.TIME_ZONE))

def choking():
	ttl = 0.0
	for lav in psutil.getloadavg():
		ttl = ttl + lav
	return (ttl > 3.0)
