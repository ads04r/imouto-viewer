from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F, Count
from django.conf import settings
from io import BytesIO
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Person, Photo, Event, EventWorkoutCategory, CalendarAppointment, LifePeriod, ImportedFile, TransitMethod, DataReading
from viewer.forms import EventForm, QuickEventForm, LifePeriodForm
from viewer.tasks.reports import generate_photo_collages
from viewer.tasks.datacrunching import regenerate_similar_events, generate_similar_events, count_event_faces, scan_event_for_text

from viewer.functions.moonshine import get_moonshine_tracks
from viewer.functions.locations import join_location_events
from viewer.functions.location_manager import getgeoline, getelevation, getspeed, getboundingbox
from viewer.functions.geo import get_area_name

import logging
logger = logging.getLogger(__name__)

def events(request):
	if request.method == 'POST':
		cache.delete('dashboard')
		form = EventForm(request.POST)
		if form.is_valid():
			event = form.save(commit=False)
			event.user = request.user
			event.save()
			try:
				tags = str(request.POST['event_tags']).split(',')
			except:
				tags = []
			for tag in tags:
				event.tag(tag.strip())
			event.workout_categories.clear()
			catid = str(request.POST['workout_type'])
			if len(catid) > 0:
				for category in EventWorkoutCategory.objects.filter(user=request.user, id=catid):
					event.workout_categories.add(category)

			return HttpResponseRedirect('./#event_' + str(event.id))
		else:
			raise Http404(form.errors)

	data = {}
	data['life'] = Event.objects.filter(user=request.user, type='life_event').order_by('-start_time')
	data['periods'] = LifePeriod.objects.order_by('type', 'start_time')
	form = EventForm()
	periodform = LifePeriodForm()
	context = {'type':'view', 'data':data, 'form':form, 'periodform': periodform, 'categories':EventWorkoutCategory.objects.filter(user=request.user)}
	return render(request, 'viewer/pages/calendar.html', context)

def event(request, eid):

	cache_key = 'event_' + str(eid)

	if request.method == 'POST':

		cache.delete('dashboard')
		data = get_object_or_404(Event, pk=eid)

		form = EventForm(request.POST, instance=data)
		if form.is_valid():
			event = form.save(commit=False)
			if event.type == 'journey':
				regenerate_similar_events(event.pk)
			try:
				peoples = str(request.POST['people'])
			except:
				peoples = ''
			if peoples == '':
				people = []
			else:
				people = peoples.split("|")
			event.people.clear()
			for id in people:
				for person in Person.objects.filter(user=request.user, uid=id):
					event.people.add(person)
			event.tags.clear()
			try:
				tags = str(request.POST['event_tags']).split(',')
			except:
				tags = []
			for tag in tags:
				tag_text = tag.strip()
				if tag_text == '':
					continue
				event.tag(tag_text)
			event.workout_categories.clear()
			try:
				catid = str(request.POST['workout_type'])
			except:
				catid = ''
			if len(catid) > 0:
				for category in EventWorkoutCategory.objects.filter(user=request.user, id=catid):
					event.workout_categories.add(category)
			event.save()

			return HttpResponseRedirect('../#event_' + str(eid))
		else:
			form = QuickEventForm(request.POST, instance=data)
			if form.is_valid():
				form.save()
				return HttpResponseRedirect('../#event_' + str(eid))
			else:
				raise Http404(form.errors)

	logger.info("Event " + str(eid) + " requested")
	data = get_object_or_404(Event, pk=eid)
	logger.debug("    ... " + str(data))
	if data.photos().count() > 0:
		count_event_faces(eid)
		scan_event_for_text(eid)

	form = EventForm(instance=data)
	context = {'type':'event', 'data':data, 'form':form, 'people':Person.objects.order_by('-significant', 'given_name', 'family_name'), 'categories':EventWorkoutCategory.objects.filter(user=request.user)}
	template = 'viewer/pages/event.html'
	if data.type=='life_event':
		template = 'viewer/pages/life_event.html'
	logger.debug("        Calling render for " + str(data))
	return render(request, template, context)

def event_music(request, eid):

	data = get_object_or_404(Event, pk=eid)
	cache_key = 'event_' + str(eid)
	music = cache.get(cache_key + '_event_music')
	if music is None:
		logger.debug("        Loading music data for " + str(data))
		music = get_moonshine_tracks(request.user, data.start_time, data.end_time)
		if len(music) > 0:
			cache.set(cache_key + '_event_music', music, 86400)
	ret = []
	for item in music:
		item['time'] = item['time'].strftime("%H:%M")
		ret.append(item)
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def event_addjourney(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	vals = request.POST['join_events'].split('_')
	catid = str(request.POST['workout_type'])
	transitid = str(request.POST['transit_type'])

	if len(vals) != 2:
		raise Http404()
	try:
		event_from = Event.objects.get(user=request.user, id=vals[0])
		event_to = Event.objects.get(user=request.user, id=vals[1])
	except:
		raise Http404()
	event = join_location_events(request.user, event_from.pk, event_to.pk)
	if event is None:
		raise Http404()
	event.geo = getgeoline(request.user, event.start_time, event.end_time)
	event.elevation = getelevation(request.user, event.start_time, event.end_time)
	event.speed = getspeed(request.user, event.start_time, event.end_time)
	event.caption = event_from.caption + ' to ' + event_to.caption
	try:
		transit_method = TransitMethod.objects.get(label__iexact=transitid)
	except TransitMethod.DoesNotExist:
		transit_method = None
	if len(catid) > 0:
		for category in EventWorkoutCategory.objects.filter(user=request.user, id=catid):
			event.workout_categories.add(category)
	if not transit_method is None:
		event.transit_method = transit_method
	event.save()
	event.auto_tag()
	ds = event.start_time.strftime("%Y%m%d")
	return HttpResponseRedirect('../#day_' + str(ds))

def event_addappointmentevent(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	try:
		c = CalendarAppointment.objects.get(user=request.user, id=request.POST['add_appointment_event'])
	except:
		c = None
	if c is None:
		raise Http404()
	else:
		event = Event(user=request.user, caption=c.caption, start_time=c.start_time, end_time=c.end_time, type='event', location=c.location, description='')
		if c.description:
			if c.description != 'None':
				event.description = c.description
		event.save()
		event.auto_tag()
		ds = event.start_time.strftime("%Y%m%d")
		return HttpResponseRedirect('../#day_' + str(ds))

def event_addfileevent(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	file_id = str(request.POST['add_file_event'])
	try:
		catid = str(request.POST['workout_type'])
	except:
		catid = ''
	imported_file = get_object_or_404(ImportedFile, pk=file_id)
	caption = 'Journey'
	if len(catid) > 0:
		caption = catid.title()
	bbox = getboundingbox(request.user, imported_file.earliest_timestamp, imported_file.latest_timestamp)
	if len(bbox) == 4:
		location_text = get_area_name(bbox[1], bbox[0], bbox[3], bbox[2])
		if len(location_text) > 0:
			caption = caption + ' in ' + location_text
	event = Event(user=request.user, caption=caption, start_time=imported_file.earliest_timestamp, end_time=imported_file.latest_timestamp, type='journey', location=None, description='')
	event.save()
	if len(catid) > 0:
		for category in EventWorkoutCategory.objects.filter(user=request.user, id=catid):
			event.workout_categories.add(category)
	event.auto_tag()

	return HttpResponseRedirect('../#event_' + str(event.pk))

def event_addactivityevent(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	ret = []
	for kk in dict(request.POST).keys():
		k = str(kk)
		if not k.startswith('activity_'):
			continue
		dr = get_object_or_404(DataReading, pk=k[9:])
		event = Event(user=request.user, caption=str(dr.type) + " activity", start_time=dr.start_time, end_time=dr.end_time, type='activity', location=None, description='')
		event.save()
		ret.append(event)

	if len(ret) == 1:
		return HttpResponseRedirect('../#event_' + str(ret[0].pk))
	return HttpResponseRedirect('../#day_' + str(ret[0].start_time.strftime("%Y%m%d")))

def event_staticmap(request, eid):
	data = get_object_or_404(Event, id=eid)
	if data.geo:
		im = data.staticmap()
		blob = BytesIO()
		im.save(blob, 'PNG')
		return HttpResponse(blob.getvalue(), content_type='image/png')
	else:
		raise Http404()

def event_gpx(request, eid):
	data = get_object_or_404(Event, id=eid)
	if data.geo:
		return HttpResponse(data.gpx(), content_type='application/xml')
	else:
		raise Http404()

def event_collage(request, eid):
	data = get_object_or_404(Event, id=eid)
	imc = data.photo_collages.count()
	if imc == 0:
		generate_photo_collages(eid)
		raise Http404()
	else:
		im = data.photo_collages.first().image
		return HttpResponse(im, content_type='image/jpeg')

def eventsplit(request, eid):
	cache_key = 'event_' + str(eid)
	if request.method != 'POST':
		raise Http404()
	id = str(request.POST['split-event'])
	if id != eid:
		raise Http404()
	ret = id
	dt = dateutil.parser.parse(request.POST['split-time'])
	mode = int(request.POST['split-split'])
	data = get_object_or_404(Event, pk=id)
	cache.delete(cache_key)

	if mode == 1:
		new_event = Event(user=request.user, caption=data.caption, type=data.type, start_time=dt, end_time=data.end_time)
		data.end_time = dt
		data.save()
		new_event.save()
		for wc in data.workout_categories.all():
			new_event.workout_categories.add(wc)
		for tag in data.tags.all():
			new_event.tags.add(tag)
		ret = str(new_event.pk)
	if mode == 2:
		data.start_time = dt
		data.save()
	if mode == 3:
		data.end_time = dt
		data.save()

	return HttpResponseRedirect('../../#event_' + str(ret))

@csrf_exempt
def eventdelete(request, eid):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(Event, pk=eid)
	dt = data.start_time.date()
	ret = data.delete()
	if 'event-id' in request.POST:
		eid_check = str(request.POST['event-id'])
	if eid == eid_check:
		response = HttpResponseRedirect('../../#day_' + dt.strftime("%Y%m%d"))
	else:
		response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def eventjson(request):
	dss = request.GET.get('start', '')
	dse = request.GET.get('end', '')
	dts = dateutil.parser.parse(dss)
	dte = dateutil.parser.parse(dse)
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []
	for event in Event.objects.filter(user=request.user, end_time__gte=dts, start_time__lte=dte):
		item = {}
		item['id'] = event.pk
		item['url'] = "#event_" + str(event.pk)
		item['title'] = event.caption
		item['start'] = event.start_time.astimezone(tz).isoformat()
		item['end'] = event.end_time.astimezone(tz).isoformat()
		item['backgroundColor'] = 'white'
		item['textColor'] = 'black'
		if event.type == 'journey':
			item['backgroundColor'] = 'green'
			item['textColor'] = 'white'
		if event.type == 'sleepover':
			item['backgroundColor'] = 'black'
			item['textColor'] = 'white'
		if event.type == 'photo':
			item['backgroundColor'] = 'orange'
			item['textColor'] = 'white'
		if event.type == 'loc_prox':
			item['backgroundColor'] = '#0073b7'
			item['textColor'] = 'white'
		if event.type == 'calendar':
			item['backgroundColor'] = '#ffc0ff'
			item['textColor'] = 'black'
		ret.append(item)
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def event_json(request, eid):
	data = get_object_or_404(Event, id=eid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def create_first_event(request):
	if Event.objects.count() == 0:
		dt = pytz.utc.localize(datetime.datetime.utcnow())
		event = Event(user=request.user, start_time=dt, end_time=dt, type='event', caption='Installed Imouto Viewer')
		event.description = "Congratulations on creating your first event!\n\nNext you'll want to start investigating the ways of importing your life into Imouto. As a good place to start, try importing a GPX or FIT file from a GPS watch using the '[Upload](./#files)' feature on the Viewer."
		event.save()
		return HttpResponseRedirect('./#event_' + str(event.pk))
	return HttpResponseRedirect('./')

def life_period(request):

	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])

	cache.delete('dashboard')

	form = LifePeriodForm(request.POST)
	if form.is_valid():

		life_period = form.save(commit=False)
		life_period.save()

		return HttpResponseRedirect('./#events')
	else:
		raise Http404(form.errors)

def transit(request, id):

	data = get_object_or_404(TransitMethod, label=id.lower())
	context = {'type':'transit', 'data':data}
	return render(request, 'viewer/pages/transit.html', context)
