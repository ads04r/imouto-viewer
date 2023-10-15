from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Day, Location, Event, EventWorkoutCategory, create_or_get_day
from viewer.forms import EventForm

from viewer.functions.moonshine import get_moonshine_tracks
from viewer.functions.locations import nearest_location
from viewer.functions.location_manager import get_possible_location_events
from viewer.functions.calendar import event_label

def day(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	Day.objects.filter(date=dt).delete()
	day = Day(date=dt)

	events = []
	potential_joins = []
	last_event = None
	for event in day.events:
		events.append(event)
		if event.type == 'journey':
			continue
		if event.type == 'sleepover':
			continue
		if not(last_event is None):
			potential_joins.append([str(last_event.pk) + '_' + str(event.pk), str(last_event.caption) + ' to ' + str(event.caption)])
		last_event = event
	for tweet in day.tweets:
		events.append(tweet)
	for sms in day.sms:
		events.append(sms)
	for commit in day.commits:
		events.append(commit)
	dss = str(day)
	events = sorted(events, key=lambda x: x.start_time if x.__class__.__name__ == 'Event' else (x.commit_date if x.__class__.__name__ == 'GitCommit' else (x['time'] if isinstance(x, (dict)) else x.time)))
	appointments = day.calendar
	context = {'type':'view', 'caption': dss, 'events':events, 'day': day, 'potential_joins': potential_joins, 'appointments': appointments, 'categories':EventWorkoutCategory.objects.all()}
	context['form'] = EventForm()
	return render(request, 'viewer/pages/day.html', context)

def day_music(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dts = datetime.datetime(y, m, d, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
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
		day = Day.objects.get(date=dt)
	except:
		day = Day(date=dt)
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
	day = create_or_get_day(dt)
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
	day = create_or_get_day(dt)
	data = day.get_sleep_information()

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
		day = Day.objects.get(date=dt)
	except:
		day = Day(date=dt)
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

def day_events(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	try:
		day = Day.objects.get(date=dt)
	except:
		day = Day(date=dt)
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
		dts = datetime.datetime.strptime(item['start'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
		dte = datetime.datetime.strptime(item['end'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
		loc = None
		if item['value']:
			if 'location' in item:
				if item['location'] > 0:
					loc = Location.objects.get(id=item['location'])
			event = Event(type='loc_prox', caption=item['text'], location=loc, start_time=dts, end_time=dte)
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
	if not('lat' in data):
		raise Http404()
	if not('lon' in data):
		raise Http404()
	ret = []
	epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
	loc = nearest_location(data['lat'], data['lon'])
	for item in get_possible_location_events(dt, data['lat'], data['lon']):
		result = {"start_time": item['start_time'].astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S"), "end_time": item['end_time'].astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")}
		result['display_text'] = (item['start_time'].strftime("%-I:%M%p") + ' to ' + item['end_time'].strftime("%-I:%M%p")).lower()
		result['text'] = result['display_text']
		if not(loc is None):
			result['display_text'] = str(loc.label) + ', ' + result['text']
			result['text'] = str(loc.label)
			result['location'] = loc.id
		appointment = event_label(item['start_time'], item['end_time'])
		if len(appointment) > 0:
			result['text'] = appointment
		ret.append(result)

	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

