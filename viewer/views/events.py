from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.tasks import regenerate_similar_events, generate_similar_events, generate_photo_collages
from viewer.models import Person, Photo, Event, EventWorkoutCategory, CalendarAppointment
from viewer.forms import EventForm, QuickEventForm

from viewer.functions.moonshine import get_moonshine_tracks
from viewer.functions.locations import join_location_events
from viewer.functions.geo import getgeoline, getelevation, getspeed

def events(request):
	if request.method == 'POST':
		cache.delete('dashboard')
		form = EventForm(request.POST)
		if form.is_valid():
			event = form.save(commit=False)
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
				for category in EventWorkoutCategory.objects.filter(id=catid):
					event.workout_categories.add(category)

			return HttpResponseRedirect('./#event_' + str(event.id))
		else:
			raise Http404(form.errors)

	data = {}
	#data['event'] = Event.objects.filter(type='event', workout_categories=None).order_by('-start_time')[0:10]
	#data['journey'] = Event.objects.filter(type='journey', workout_categories=None).order_by('-start_time')[0:10]
	#data['workout'] = Event.objects.exclude(workout_categories=None).order_by('-start_time')[0:10]
	#data['photo'] = Event.objects.filter(type='photo').exclude(caption='Photos').order_by('-start_time')[0:10]
	data['life'] = Event.objects.filter(type='life_event').order_by('-start_time')
	form = EventForm()
	context = {'type':'view', 'data':data, 'form':form, 'categories':EventWorkoutCategory.objects.all()}
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
				for person in Person.objects.filter(uid=id):
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
				for category in EventWorkoutCategory.objects.filter(id=catid):
					event.workout_categories.add(category)
			event.save()

			#cache.set(cache_key, data, 86400)
			return HttpResponseRedirect('../#event_' + str(eid))
		else:
			form = QuickEventForm(request.POST, instance=data)
			if form.is_valid():
				form.save()
				#cache.set(cache_key, data, 86400)
				return HttpResponseRedirect('../#event_' + str(eid))
			else:
				raise Http404(form.errors)

	#data = cache.get(cache_key)
	#if data is None:
	data = get_object_or_404(Event, pk=eid)
	#	cache.set(cache_key, data, 86400)

	form = EventForm(instance=data)
	context = {'type':'event', 'data':data, 'form':form, 'people':Person.objects.all(), 'categories':EventWorkoutCategory.objects.all()}
	music = cache.get(cache_key + '_music')
	if music is None:
		music = get_moonshine_tracks(data.start_time, data.end_time)
		if len(music) > 0:
			cache.set(cache_key + '_music', music, 86400)
		else:
			music = False
			cache.set(cache_key + '_music', music, 86400)
	if music:
		context['music'] = music
	template = 'viewer/pages/event.html'
	if data.type=='life_event':
		template = 'viewer/pages/lifeevent.html'
	return render(request, template, context)

def event_addjourney(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	vals = request.POST['join_events'].split('_')
	catid = str(request.POST['workout_type'])

	if len(vals) != 2:
		raise Http404()
	try:
		event_from = Event.objects.get(id=vals[0])
		event_to = Event.objects.get(id=vals[1])
	except:
		raise Http404()
	event = join_location_events(event_from.pk, event_to.pk)
	if event is None:
		raise Http404()
	event.geo = getgeoline(event.start_time, event.end_time)
	event.elevation = getelevation(event.start_time, event.end_time)
	event.speed = getspeed(event.start_time, event.end_time)
	event.caption = event_from.caption + ' to ' + event_to.caption
	if len(catid) > 0:
		for category in EventWorkoutCategory.objects.filter(id=catid):
			event.workout_categories.add(category)
	event.save()
	event.auto_tag()
	ds = event.start_time.strftime("%Y%m%d")
	return HttpResponseRedirect('../#day_' + str(ds))

def event_addappointmentevent(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	try:
		c = CalendarAppointment.objects.get(id=request.POST['add_appointment_event'])
	except:
		c = None
	if c is None:
		raise Http404()
	else:
		event = Event(caption=c.caption, start_time=c.start_time, end_time=c.end_time, type='event', location=c.location, description='')
		if c.description:
			if c.description != 'None':
				event.description = c.description
		event.save()
		event.auto_tag()
		ds = event.start_time.strftime("%Y%m%d")
		return HttpResponseRedirect('../#day_' + str(ds))

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

@csrf_exempt
def eventdelete(request, eid):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(Event, pk=eid)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def eventjson(request):
	dss = request.GET.get('start', '')
	dse = request.GET.get('end', '')
	dts = dateutil.parser.parse(dss)
	dte = dateutil.parser.parse(dse)
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []
	for event in Event.objects.filter(end_time__gte=dts).filter(start_time__lte=dte):
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
		event = Event(start_time=dt, end_time=dt, type='event', caption='Installed Imouto Viewer')
		event.description = "Congratulations on creating your first event!\n\nNext you'll want to start investigating the ways of importing your life into Imouto. As a good place to start, try importing a GPX or FIT file from a GPS watch using the '[Upload](./#files)' feature on the Viewer."
		event.save()
		return HttpResponseRedirect('./#event_' + str(event.pk))
	return HttpResponseRedirect('./')
