from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F, DurationField, ExpressionWrapper, Max
from django.db.models.functions import Cast
from django.db.models.fields import DateField
from django.conf import settings
from rest_framework.exceptions import MethodNotAllowed
from background_task.models import Task
from haystack.query import SearchQuerySet
from viewer.tasks import generate_photo_collages
import datetime, pytz, dateutil.parser, json, tzlocal, requests

from .tasks import *
from .models import *
from .forms import *
from .functions import *

def index(request):
	context = {'type':'index', 'data':[]}
	return render(request, 'viewer/index.html', context)

def upload_file(request):
	if request.method != 'POST':
		raise MethodNotAllowed(str(request.method))
	url = settings.LOCATION_MANAGER_URL + '/import'
	files = {'uploaded_file': request.FILES['uploadformfile']}
	data = {'file_source': request.POST['uploadformfilesource']}

	r = requests.post(url, files=files, data=data)
	return HttpResponseRedirect('./#files')

def script(request):
	context = {'tiles': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
	if hasattr(settings, 'MAP_TILES'):
		if settings.MAP_TILES != '':
			context['tiles'] = str(settings.MAP_TILES)
	return render(request, 'viewer/imouto.js', context=context, content_type='text/javascript')

def dashboard(request):
	key = 'dashboard'
	ret = cache.get(key)
	if ret is None:
		data = generate_dashboard()
		context = {'type':'view', 'data':data}
		ret = render(request, 'viewer/dashboard.html', context)
		cache.set(key, ret, timeout=86400)
	return ret

def imouto_json_serializer(data):
	if isinstance(data, datetime.datetime):
		return data.strftime("%Y-%m-%d %H:%M:%S %Z")
	if isinstance(data, (Person, Location, Event)):
		return data.to_dict()

def dashboard_json(request):
	data = generate_dashboard()
	if 'heart' in data:
		data['heart'] = json.loads(data['heart'])
	if 'steps' in data:
		data['steps'] = json.loads(data['steps'])
	if 'sleep' in data:
		data['sleep'] = json.loads(data['sleep'])
	response = HttpResponse(json.dumps(data, default=imouto_json_serializer), content_type='application/json')
	return response

def onthisday(request, format='html'):
	key = 'onthisday_' + datetime.date.today().strftime("%Y%m%d")
	data = cache.get(key)
	if data is None:
		data = generate_onthisday()
		cache.set(key, data, timeout=86400)
	context = {'type':'view', 'data':data}
	return render(request, 'viewer/onthisday.html', context)

def importer(request):
	url = settings.LOCATION_MANAGER_URL + '/import'
	r = requests.get(url=url)
	context = {'progress': r.json()}
	return render(request, 'viewer/import.html', context)

def report_queue(request):
	data = get_report_queue()
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def timeline(request):
	dt = Event.objects.order_by('-start_time')[0].start_time
	ds = dt.strftime("%Y%m%d")
	form = QuickEventForm()
	context = {'type':'view', 'data':{'current': ds}, 'form':form}
	return render(request, 'viewer/timeline.html', context)

def health_data(datatypes):
	item = {'date': ''}
	filter = None
	ret = []
	for type in datatypes:
		if filter is None:
			filter = Q(type=type)
		else:
			filter = filter | Q(type=type)
	for dr in DataReading.objects.filter(filter).order_by('-start_time'):
		type = str(dr.type)
		if type == 'weight':
			value = float(dr.value) / 1000
		else:
			value = int(dr.value)
		if dr.start_time != item['date']:
			if item['date'] != '':
				ret.append(item)
			item = {'date': dr.start_time}
		item[type] = value
	ret.append(item)
	return ret

@csrf_exempt
def health(request, pageid):
	context = {'type':'view', 'page': pageid, 'data':[]}
	if pageid == 'heart':
		return render(request, 'viewer/health_heart.html', context)
	if pageid == 'sleep':
		dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC)
		expression = F('end_time') - F('start_time')
		wrapped_expression = ExpressionWrapper(expression, DurationField())
		context['data'] = {'stats': [], 'sleeps': []}
		for days in [7, 28, 365]:
			context['data']['stats'].append({'label': 'week', 'graph': get_sleep_history(days), 'best_sleep': DataReading.objects.filter(type='sleep', value='2', start_time__gte=(dt - datetime.timedelta(days=days))).annotate(length=wrapped_expression).order_by('-length')[0].start_time, 'earliest_waketime': DataReading.objects.filter(start_time__gte=(dt - datetime.timedelta(days=days)), type='awake').extra(select={'time': 'TIME(start_time)'}).order_by('time')[0].start_time, 'latest_waketime': DataReading.objects.filter(start_time__gte=(dt - datetime.timedelta(days=days)), type='awake').extra(select={'time': 'TIME(start_time)'}).order_by('-time')[0].start_time, 'earliest_bedtime': DataReading.objects.filter(start_time__gte=(dt - datetime.timedelta(days=days)), type='awake').extra(select={'time': 'TIME(end_time)'}).order_by('time')[0].end_time, 'latest_bedtime': DataReading.objects.filter(start_time__gte=(dt - datetime.timedelta(days=days)), type='awake').extra(select={'time': 'TIME(end_time)'}).order_by('-time')[0].end_time})
		context['data']['midpoint'] = context['data']['stats'][2]['latest_waketime']
		return render(request, 'viewer/health_sleep.html', context)
	if pageid == 'distance':
		return render(request, 'viewer/health_distance.html', context)
	if pageid == 'schedule':
		dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC)
		context['events'] = Event.objects.filter(start_time__gte=(dt - datetime.timedelta(days=28))).exclude(workout_categories=None).order_by('-start_time')[0:10]
		return render(request, 'viewer/health_schedule.html', context)
	if pageid == 'blood':
		if request.method == 'POST':
			ret = json.loads(request.body)
			dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=pytz.UTC)
			datapoint = DataReading(type='bp_sys', start_time=dt, end_time=dt, value=ret['bp_sys_val'])
			datapoint.save()
			datapoint = DataReading(type='bp_dia', start_time=dt, end_time=dt, value=ret['bp_dia_val'])
			datapoint.save()
			response = HttpResponse(json.dumps(ret), content_type='application/json')
			return response
		context['data'] = health_data(['bp_sys', 'bp_dia'])
		return render(request, 'viewer/health_bp.html', context)
	if pageid == 'weight':
		context['data'] = health_data(['weight', 'fat', 'muscle', 'water'])
		context['graphs'] = {}
		dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC)
		for i in [{'label': 'week', 'dt': (dt - datetime.timedelta(days=7))}, {'label': 'month', 'dt': (dt - datetime.timedelta(days=28))}, {'label': 'year', 'dt': (dt - datetime.timedelta(days=365))}]:
			item = []
			min_dt = i['dt'].timestamp()
			for point in DataReading.objects.filter(type='weight', end_time__gte=i['dt']).order_by('start_time'):
				pdt = point.start_time.timestamp()
				if pdt < min_dt:
					continue
				item.append({'x': pdt, 'y': (float(point.value) / 1000)})
			context['graphs'][i['label']] = json.dumps(item)
		return render(request, 'viewer/health_weight.html', context)
	if pageid == 'mentalhealth':
		if request.method == 'POST':
			ret = json.loads(request.body)
			dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=pytz.UTC)
			datapoint = DataReading(type='hads-a', start_time=dt, end_time=dt, value=ret['anxiety'])
			datapoint.save()
			datapoint = DataReading(type='hads-d', start_time=dt, end_time=dt, value=ret['depression'])
			datapoint.save()
			response = HttpResponse(json.dumps(ret), content_type='application/json')
			return response
		for entry in health_data(['hads-a', 'hads-d']):
			item = {'date': entry['date']}
			if 'hads-a' in entry:
				item['anxiety'] = entry['hads-a']
			if 'hads-d' in entry:
				item['depression'] = entry['hads-d']
			context['data'].append(item)
		return render(request, 'viewer/health_mentalhealth.html', context)
	return render(request, 'viewer/health.html', context)

def timelineitem(request, ds):
	dsyear = int(ds[0:4])
	dsmonth = int(ds[4:6])
	dsday = int(ds[6:])
	dtq = datetime.datetime(dsyear, dsmonth, dsday, 0, 0, 0, tzinfo=tzlocal.get_localzone())
	events = get_timeline_events(dtq)

	dtq = events[0].start_time
	dtn = dtq - datetime.timedelta(days=1)
	dsq = dtq.strftime("%Y%m%d")
	dsn = dtn.strftime("%Y%m%d")

	context = {'type':'view', 'data':{'label': dtq.strftime("%A %-d %B"), 'id': dsq, 'next': dsn, 'events': events}}
	return render(request, 'viewer/timeline_event.html', context)

def reports(request):
	if request.method == 'POST':
		form = CreateReportForm(request.POST)
		if form.is_valid():
			year = int(request.POST['year'])
			dss = datetime.datetime(year, 1, 1, 0, 0, 0, tzinfo=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %z")
			dse = datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %z")
			title = str(request.POST['label'])
			style = str(request.POST['style'])
			options = {}
			options['reportdetail'] = request.POST['reportdetail']
			options['peoplestats'] = False
			options['wordcloud'] = False
			options['maps'] = False
			if 'peoplestats' in request.POST:
				if request.POST['peoplestats'] == 'on':
					options['peoplestats'] = True
			if 'wordcloud' in request.POST:
				if request.POST['wordcloud'] == 'on':
					options['wordcloud'] = True
			if 'maps' in request.POST:
				if request.POST['maps'] == 'on':
					options['maps'] = True
			if 'moonshine_url' in request.POST:
				generate_report(title, dss, dse, options, 'year', style, str(request.POST['moonshine_url']))
			else:
				generate_report(title, dss, dse, options, 'year', style)
			return HttpResponseRedirect('./#reports')
		else:
			raise Http404(form.errors)

	form = CreateReportForm()
	data = LifeReport.objects.all().order_by('-modified_date')
	context = {'type':'view', 'data':data, 'form': form, 'settings': {}, 'years': []}
	y1 = Event.objects.all().order_by('start_time')[0].start_time.year + 1
	y2 = Event.objects.all().order_by('-start_time')[0].start_time.year - 1
	for y in range(y2, y1 - 1, -1):
		context['years'].append(y)
	if hasattr(settings, 'MOONSHINE_URL'):
		if settings.MOONSHINE_URL != '':
			context['settings']['moonshine_url'] = settings.MOONSHINE_URL
	return render(request, 'viewer/reports.html', context)

def events(request):
	if request.method == 'POST':
		cache.delete('dashboard')
		form = EventForm(request.POST)
		if form.is_valid():
			event = form.save(commit=False)
			if event.type == 'journey':
				event.geo = getgeoline(event.start_time, event.end_time)
				event.elevation = getelevation(event.start_time, event.end_time)
				event.speed = getspeed(event.start_time, event.end_time)
				event.cached_health = ''
			event.save()
			event.tags.clear()
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
			event.save()
			event.populate_people_from_photos()

			return HttpResponseRedirect('./#event_' + str(event.id))
		else:
			raise Http404(form.errors)

	data = {}
	data['event'] = Event.objects.filter(type='event', workout_categories=None).order_by('-start_time')[0:10]
	data['journey'] = Event.objects.filter(type='journey', workout_categories=None).order_by('-start_time')[0:10]
	data['workout'] = Event.objects.exclude(workout_categories=None).order_by('-start_time')[0:10]
	data['photo'] = Event.objects.filter(type='photo').exclude(caption='Photos').order_by('-start_time')[0:10]
	data['life'] = Event.objects.filter(type='life_event').order_by('-start_time')
	form = EventForm()
	context = {'type':'view', 'data':data, 'form':form, 'categories':EventWorkoutCategory.objects.all()}
	return render(request, 'viewer/calendar.html', context)

def tags(request):

	data = EventTag.objects.annotate(num_events=Count('events')).order_by('-num_events')
	context = {'type':'tag', 'data':data}
	return render(request, 'viewer/tags.html', context)

def tag(request, id):

	data = get_object_or_404(EventTag, id=id)
	context = {'type':'tag', 'data':data}
	return render(request, 'viewer/tag.html', context)

def day(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dts = datetime.datetime(y, m, d, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = dts + datetime.timedelta(seconds=86400)
	dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
	events = []
	for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by('start_time'):
		events.append(event)
	for tweet in RemoteInteraction.objects.filter(time__gte=dts, time__lte=dte, type='microblogpost', address='').order_by('time'):
		events.append(tweet)
	for sms in RemoteInteraction.objects.filter(time__gte=dts, time__lte=dte, type='sms').order_by('time'):
		events.append(sms)
	dss = dts.strftime('%A, %-d %B %Y')
	events = sorted(events, key=lambda x: x.start_time if x.__class__.__name__ == 'Event' else (x['time'] if isinstance(x, (dict)) else x.time))
	context = {'type':'view', 'caption': dss, 'events':events, 'stats': {}}
	wakes = DataReading.objects.filter(type='awake', start_time__lt=dte, end_time__gt=dts).order_by('start_time')
	wakecount = wakes.count()
	if wakecount > 0:
		context['stats']['wake_time'] = wakes[0].start_time
		context['stats']['sleep_time'] = wakes[(wakecount - 1)].end_time
	context['stats']['prev'] = (dts - datetime.timedelta(days=1)).strftime("%Y%m%d")
	context['stats']['cur'] = dts.strftime("%Y%m%d")
	for weight in DataReading.objects.filter(end_time__gte=dts, start_time__lte=dte, type='weight'):
		if not('weight' in context['stats']):
			context['stats']['weight'] = []
		context['stats']['weight'].append({"time": weight.start_time, "weight": (float(weight.value) / 1000)})
	if dte < dt:
		context['stats']['next'] = (dts + datetime.timedelta(days=1)).strftime("%Y%m%d")
	return render(request, 'viewer/day.html', context)

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
	dts = datetime.datetime(y, m, d, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = dts + datetime.timedelta(seconds=86400)
	dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
	data = []
	for weight in DataReading.objects.filter(end_time__gte=dts, start_time__lte=dte, type='weight'):
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
	data = get_heart_information(dt)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_sleep(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dt = datetime.date(y, m, d)
	data = get_sleep_information(dt)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def day_people(request, ds):

	if len(ds) != 8:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:6])
	d = int(ds[6:])
	dts = datetime.datetime(y, m, d, 0, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = datetime.datetime(y, m, d, 23, 59, 59, tzinfo=pytz.timezone(settings.TIME_ZONE))
	data = []
	people = []
	for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by('start_time'):
		for person in event.people.all():
			if person.uid in people:
				continue
			people.append(person.uid)
	for uid in people:
		person = Person.objects.get(uid=uid)
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
	dts = datetime.datetime(y, m, d, 0, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = datetime.datetime(y, m, d, 23, 59, 59, tzinfo=pytz.timezone(settings.TIME_ZONE))
	data = []
	for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by('start_time'):
		data.append(event.to_dict())

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

@csrf_exempt
def day_locevents(request, ds):

	if request.method != 'POST':
		raise MethodNotAllowed(str(request.method))
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
		result = {"start_time": item['start_time'].strftime("%Y-%m-%d %H:%M:%S"), "end_time": item['end_time'].strftime("%Y-%m-%d %H:%M:%S")}
		result['text'] = (item['start_time'].strftime("%-I:%M%p") + ' to ' + item['end_time'].strftime("%-I:%M%p")).lower()
		if not(loc is None):
			result['text'] = str(loc.label) + ', ' + result['text']
			result['location'] = loc.id
		ret.append(result)

	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def event(request, eid):

	cache_key = 'event_' + str(eid)

	if request.method == 'POST':

		cache.delete('dashboard')
		data = get_object_or_404(Event, pk=eid)

		form = EventForm(request.POST, instance=data)
		if form.is_valid():
			event = form.save(commit=False)
			if event.type == 'journey':
				event.geo = getgeoline(event.start_time, event.end_time)
				event.elevation = getelevation(event.start_time, event.end_time)
				event.speed = getspeed(event.start_time, event.end_time)
			event.tags.clear()
			try:
				tags = str(request.POST['event_tags']).split(',')
			except:
				tags = []
			for tag in tags:
				event.tag(tag.strip())
			event.workout_categories.clear()
			try:
				catid = str(request.POST['workout_type'])
			except:
				catid = ''
			if len(catid) > 0:
				for category in EventWorkoutCategory.objects.filter(id=catid):
					event.workout_categories.add(category)
			event.cached_health = ''
			event.save()
			event.populate_people_from_photos()

			cache.set(cache_key, data, 86400)
			return HttpResponseRedirect('../#event_' + str(eid))
		else:
			form = QuickEventForm(request.POST, instance=data)
			if form.is_valid():
				form.save()
				cache.set(cache_key, data, 86400)
				return HttpResponseRedirect('../#event_' + str(eid))
			else:
				raise Http404(form.errors)

	data = cache.get(cache_key)
	if data is None:
		data = get_object_or_404(Event, pk=eid)
		cache.set(cache_key, data, 86400)

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
	template = 'viewer/event.html'
	if data.type=='life_event':
		template = 'viewer/lifeevent.html'
	return render(request, template, context)

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

@csrf_exempt
def reportdelete(request, rid):
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(LifeReport, pk=rid)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

@csrf_exempt
def eventpeople(request):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	eid = request.POST['id']
	pids = request.POST['people'].split('|')
	data = get_object_or_404(Event, pk=eid)
	people = []
	for pid in pids:
		people.append(get_object_or_404(Person, uid=pid))
	data.people.clear()
	for person in people:
		data.people.add(person)
		key = 'person_' + str(person.uid) + '_' + datetime.date.today().strftime("%Y%m%d")
		cache.delete(key)
	return HttpResponseRedirect('./#event_' + str(data.id))

def eventjson(request):
	dss = request.GET.get('start', '')
	dse = request.GET.get('end', '')
	dts = dateutil.parser.parse(dss)
	dte = dateutil.parser.parse(dse)
	tz = tzlocal.get_localzone()
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

def places(request):
	data = {}
	datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=60)
	data['recent'] = Location.objects.filter(events__start_time__gte=datecutoff).annotate(num_events=Count('events')).order_by('-num_events')
	data['all'] = Location.objects.annotate(num_events=Count('events')).order_by('label')
	if request.method == 'POST':
		cache.delete('dashboard')
		form = LocationForm(request.POST, request.FILES)
		if form.is_valid():
			post = form.save(commit=False)
			id = form.cleaned_data['uid']
			if form.cleaned_data.get('uploaded_image'):
				#image = Image(title=post.full_label, description=post.description, image=request.FILES['uploaded_image'])
				#image.save()
				post.image = request.FILES['uploaded_image']
			post.save()
			return HttpResponseRedirect('./#place_' + str(id))
		else:
			raise Http404(form.errors)
	else:
		form = LocationForm()
	context = {'type':'place', 'data':data, 'form':form}
	return render(request, 'viewer/places.html', context)

def place(request, uid):
	key = 'place_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
	ret = cache.get(key)
	if ret is None:
		data = get_object_or_404(Location, uid=uid)
		context = {'type':'place', 'data':data}
		ret = render(request, 'viewer/place.html', context)
		cache.set(key, ret, timeout=86400)
	return ret

def people(request):
	data = {}
	datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=365)
	data['recent_by_events'] = Person.objects.filter(event__start_time__gte=datecutoff).annotate(num_events=Count('event', distinct=True)).order_by('-num_events')[0:10]
	data['recent_by_days'] = Person.objects.filter(event__start_time__gte=datecutoff).annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).order_by('-days')[0:10]
	data['recent_by_last_seen'] = Person.objects.annotate(last_seen=Max('event__start_time')).order_by('-last_seen')[0:10]
	data['photos'] = Person.objects.filter(photo__time__gte=datecutoff).annotate(photo_count=Count('photo')).order_by('-photo_count')[0:10]
	data['messages'] = []
	data['calls'] = []
	for number in RemoteInteraction.objects.filter(time__gte=datecutoff, type='sms').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['messages'].append([person, number['messages']])
	for number in RemoteInteraction.objects.filter(time__gte=datecutoff, type='phone-call').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
		try:
			person = Person.objects.get(properties__key='phone', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
	data['all'] = Person.objects.annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).annotate(last_seen=Max('event__start_time')).order_by('given_name', 'family_name')
	context = {'type':'person', 'data':data}
	ret = render(request, 'viewer/people.html', context)
	return ret

def person(request, uid):
	key = 'person_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
	ret = cache.get(key)
	if ret is None:
		data = get_object_or_404(Person, uid=uid)
		context = {'type':'person', 'data':data, 'properties':explode_properties(data)}
		ret = render(request, 'viewer/person.html', context)
		cache.set(key, ret, timeout=86400)
	return ret

def report(request, id):
	data = get_object_or_404(LifeReport, id=id)
	context = {'type':'report', 'data':data}
	return render(request, 'viewer/report.html', context)

def report_pdf(request, id):
	data = get_object_or_404(LifeReport, id=id)
	pdf = open(data.pdf.path, 'rb')
	response = HttpResponse(content=pdf)
	response['Content-Type'] = 'application/pdf'
	response['Content-Disposition'] = 'attachment; filename="%s.pdf"' % str(data)
	return response

def report_words(request, id):
	data = get_object_or_404(LifeReport, id=id)
	txt = data.words()
	response = HttpResponse(content=txt, content_type='text/plain')
	return response

def report_wordcloud(request, id):
	data = get_object_or_404(LifeReport, id=id)
	im = data.wordcloud()
	response = HttpResponse(content_type='image/png')
	im.save(response, "PNG")
	return response

def person_photo(request, uid):
	data = get_object_or_404(Person, uid=uid)
	im = data.photo()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def place_photo(request, uid):
	data = get_object_or_404(Location, uid=uid)
	im = data.photo()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def photo_json(request, uid):
	data = get_object_or_404(Photo, pk=uid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def photo_full(request, uid):
	data = get_object_or_404(Photo, pk=uid)
	im = data.image()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def photo_thumbnail(request, uid):
	data = get_object_or_404(Photo, pk=uid)
	im = data.thumbnail(200)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def person_thumbnail(request, uid):
	data = get_object_or_404(Person, uid=uid)
	im = data.thumbnail(100)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def place_thumbnail(request, uid):
	data = get_object_or_404(Location, uid=uid)
	im = data.thumbnail(100)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

@csrf_exempt
def search(request):
	if request.method != 'POST':
		raise Http404()
	data = json.loads(request.body)
	query = data['query']
	ret = []

	cache_key = 'search_' + query
	sq = cache.get(cache_key)
	if sq is None:
		sq = SearchQuerySet().filter(content=query).order_by('-start_time')[0:50]
		cache.set(cache_key, sq, 86400)

	for searchresult in sq:
		event = searchresult.object
		description = event.description[0:50]
		if len(description) == 50:
			description = description[0:(description.rfind(' '))]
			if len(description) > 0:
				description = description + ' ...'
		if description == '':
			description = event.start_time.strftime("%a %-d %b %Y")
		item = {'label': event.caption, 'id': event.id, 'description': description, 'date': event.start_time.strftime("%A %-d %B"), 'type': event.type, 'link': 'event_' + str(event.id)}
		ret.append(item)
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def event_json(request, eid):
	data = get_object_or_404(Event, id=eid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def reports_json(request):
	data = []
	for report in LifeReport.objects.all():
		item = {'id': report.id, 'label': report.label, 'year': report.year(), 'pdf': False, 'style': report.style, 'options': json.loads(report.options)}
		if report.pdf:
			if os.path.exists(report.pdf.path):
				item['pdf'] = True
		data.append(item)
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def report_json(request, id):
	data = get_object_or_404(LifeReport, id=id)
	ret = data.to_dict()
	ret['pages'] = data.pages()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def person_json(request, uid):
	data = get_object_or_404(Person, uid=uid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def place_json(request, uid):
	data = get_object_or_404(Location, uid=uid)
	data_dict = data.to_dict()
	data_dict['internal_id'] = data.pk
	response = HttpResponse(json.dumps(data_dict), content_type='application/json')
	return response

def locman_import(request):
	url = settings.LOCATION_MANAGER_URL + '/import'
	r = requests.get(url)
	r.raise_for_status()
	response = HttpResponse(r.text, content_type='application/json')
	return response

def locman_process(request):
	url = settings.LOCATION_MANAGER_URL + '/process'
	r = requests.get(url)
	r.raise_for_status()
	response = HttpResponse(r.text, content_type='application/json')
	return response

