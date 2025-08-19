from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Day, Location, Event, EventWorkoutCategory, HistoricalEvent, ImportedFile, create_or_get_day
from viewer.forms import EventForm

from viewer.functions.moonshine import get_moonshine_tracks
from viewer.functions.locations import nearest_location
from viewer.functions.location_manager import get_possible_location_events, getamenities
from viewer.functions.calendar import event_label

import logging
logger = logging.getLogger(__name__)

def day(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	now = pytz.utc.localize(datetime.datetime.utcnow())
	Day.objects.filter(user=request.user, date=dt).delete()
	day = Day(user=request.user, date=dt)
	day.refresh()

	events = []
	potential_joins = []
	last_event = None
	for event in day.events:
		event.start_time = event.start_time.astimezone(day.timezone)
		events.append(event)
		if event.type == 'journey':
			continue
		if event.type == 'sleepover':
			continue
		if not(last_event is None):
			potential_joins.append([str(last_event.pk) + '_' + str(event.pk), str(last_event.caption) + ' to ' + str(event.caption)])
		last_event = event
	for msg in day.microblogposts:
		events.append(msg)
	for sms in day.sms:
		events.append(sms)
	for im in day.im:
		events.append(im)
	for commit in day.commits:
		events.append(commit)
	for task in day.tasks_completed:
		task.time_completed = task.time_completed.astimezone(day.timezone)
		events.append(task)
	if day.sunrise_time:
		if day.sunrise_time < now:
			events.append({'type': 'sun_time', 'time': day.sunrise_time.astimezone(day.timezone), 'value': 'sunrise'})
	if day.sunset_time:
		if day.sunset_time < now:
			events.append({'type': 'sun_time', 'time': day.sunset_time.astimezone(day.timezone), 'value': 'sunset'})
	dss = str(day)
	events = sorted(events, key=lambda x: x.start_time if x.__class__.__name__ == 'Event' else (x.time_completed if x.__class__.__name__ == 'CalendarTask' else (x.commit_date if x.__class__.__name__ == 'GitCommit' else (x['time'] if isinstance(x, (dict)) else x.time))))
	appointments = day.calendar
	amenities = getamenities(request.user, day.date)
	imported_files = ImportedFile.objects.filter(user=request.user, latest_timestamp__gte=pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(day.date.year, day.date.month, day.date.day, 0, 0, 0)), earliest_timestamp__lte=pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(day.date.year, day.date.month, day.date.day, 23, 59, 59))).order_by('earliest_timestamp')
	context = {'type':'view', 'caption': dss, 'events':events, 'day': day, 'potential_joins': potential_joins, 'appointments': appointments, 'categories':EventWorkoutCategory.objects.filter(user=request.user), 'amenities': amenities, 'imported_files': imported_files}
	context['form'] = EventForm()
	return render(request, 'viewer/pages/day.html', context)

def day_card(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	day = create_or_get_day(request.user, dt)
	dss = str(day)
	context = {'type':'view', 'caption': dss, 'day': day, 'history': HistoricalEvent.objects.filter(date=dt)}
	context['form'] = EventForm()
	return render(request, 'viewer/cards/day.html', context)

def day_music(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(y, m, d, 4, 0, 0))
	dte = dts + datetime.timedelta(seconds=86400)

	data = []
	for item in get_moonshine_tracks(dts, dte):
		item['time'] = item['time'].strftime("%H:%M")
		data.append(item)
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_weight(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	try:
		day = Day.objects.get(user=request.user, date=dt)
	except:
		day = Day(user=request.user, date=dt)
		day.save()

	data = []
	for weight in day.data_readings('weight'):
		data.append({"time": weight.start_time.astimezone(tz=pytz.timezone(settings.TIME_ZONE)).strftime("%H:%M"), "date": weight.start_time.strftime("%Y-%m-%dT%H:%M:%S%z"), "weight": (float(weight.value) / 1000)})

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_heart(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	day = create_or_get_day(request.user, dt)
	data = day.get_heart_information()

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_sleep(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	day = create_or_get_day(request.user, dt)
	if day is None:
		data = {}
	else:
		day.cached_sleep = None
		data = day.get_sleep_information()

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_data(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	try:
		day = Day.objects.get(user=request.user, date=dt)
	except:
		day = Day(user=request.user, date=dt)
		day.save()

	data = []
	for item in day.data_readings().order_by('start_time'):
		data.append({"date": item.start_time.astimezone(tz=pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d"), "start_time": item.start_time.astimezone(tz=pytz.timezone(settings.TIME_ZONE)).strftime("%H:%M:%S"), "end_time": item.end_time.astimezone(tz=pytz.timezone(settings.TIME_ZONE)).strftime("%H:%M:%S"), "type": item.type, "value": item.value})

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_people(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	try:
		day = Day.objects.get(user=request.user, date=dt)
	except:
		day = Day(user=request.user, date=dt)
		day.save()

	data = []
	for person in day.people:
		info = person.to_dict()
		info['image'] = False
		if person.image:
			info['image'] = True
		data.append(info)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_amenities(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)

	data = getamenities(dt)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_events(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	try:
		day = Day.objects.get(user=request.user, date=dt)
	except:
		day = Day(user=request.user, date=dt)
		day.save()

	data = []
	for event in day.events:
		data.append(event.to_dict())

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

@csrf_exempt
def day_loceventscreate(request, ds):

	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	data = json.loads(request.body)
	ret = []
	for item in data:
		dts = pytz.utc.localize(datetime.datetime.strptime(item['start'], "%Y-%m-%d %H:%M:%S"))
		dte = pytz.utc.localize(datetime.datetime.strptime(item['end'], "%Y-%m-%d %H:%M:%S"))
		loc = None
		if item['value']:
			if 'location' in item:
				if isinstance(item['location'], int):
					if item['location'] > 0:
						loc = Location.objects.get(user=request.user, id=item['location'])
			event = Event(user=request.user, type='loc_prox', caption=item['text'], location=loc, start_time=dts, end_time=dte)
			event.save()
			event.auto_tag()
			ret.append(event.id)
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

@csrf_exempt
def day_locevents(request, ds):

	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	data = json.loads(request.body)
	lookup = False
	if 'lookup' in data:
		lookup = data['lookup'];
	if not('lat' in data):
		raise Http404()
	if not('lon' in data):
		raise Http404()
	ret = []
	epoch = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	loc = None
	if lookup:
		loc = nearest_location(request.user, data['lat'], data['lon'])
	for item in get_possible_location_events(request.user, dt, data['lat'], data['lon']):
		result = {"start_time": item['start_time'].astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S"), "end_time": item['end_time'].astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")}
		result['display_text'] = (item['start_time'].strftime("%-I:%M%p") + ' to ' + item['end_time'].strftime("%-I:%M%p")).lower()
		result['text'] = result['display_text']
		if not(loc is None):
			result['display_text'] = str(loc.label) + ', ' + result['text']
			result['text'] = str(loc.label)
			result['location'] = loc.id
		appointment = event_label(request.user, item['start_time'], item['end_time'])
		if len(appointment) > 0:
			result['text'] = appointment
		ret.append(result)

	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

