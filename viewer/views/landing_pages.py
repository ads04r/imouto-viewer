from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from django.db.models import Q, F
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Event
from viewer.forms import EventForm, QuickEventForm

from viewer.functions.locations import home_location
from viewer.functions.utils import get_timeline_events, generate_dashboard, generate_onthisday, imouto_json_serializer

import logging
logger = logging.getLogger(__name__)

def index(request):
	context = {'type':'index', 'data':[]}
	logger.info("HTML frame requested")
	return render(request, 'viewer/index.html', context)

def dashboard(request):
	logger.info("Dashboard requested")
	key = 'dashboard'
	ret = cache.get(key)
	if ret is None:
		logger.debug("Generating dashboard")
		data = generate_dashboard()
		context = {'type':'view', 'data':data}
		if len(data) == 0:
			ret = render(request, 'viewer/pages/setup.html', context)
		elif 'error' in data:
			ret = render(request, 'viewer/pages/dashboard_error.html', context)
		else:
			ret = render(request, 'viewer/pages/dashboard.html', context)
			cache.set(key, ret, timeout=86400)
		logger.debug("Dashboard generated")
	else:
		logger.debug("Getting cached dashboard")
	return ret

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

def script(request):
	context = {'tiles': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 'home': home_location()}
	if hasattr(settings, 'MAP_TILES'):
		if settings.MAP_TILES != '':
			context['tiles'] = str(settings.MAP_TILES)
	return render(request, 'viewer/imouto.js', context=context, content_type='text/javascript')

def timeline(request):
	try:
		dt = Event.objects.order_by('-start_time')[0].start_time
	except:
		return render(request, 'viewer/pages/setup.html', {})
	logger.info("Timeline requested")
	ds = dt.strftime("%Y%m%d")
	form = QuickEventForm()
	context = {'type':'view', 'data':{'current': ds}, 'form':form}
	return render(request, 'viewer/pages/timeline.html', context)

def timelineitem(request, ds):
	dsyear = int(ds[0:4])
	dsmonth = int(ds[4:6])
	dsday = int(ds[6:])
	dtq = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(dsyear, dsmonth, dsday, 0, 0, 0))
	events = get_timeline_events(dtq)

	dtq = events[0].start_time
	dtn = dtq - datetime.timedelta(days=1)
	dsq = dtq.strftime("%Y%m%d")
	dsn = dtn.strftime("%Y%m%d")

	logger.info("Timeline items requested for " + dtq.strftime("%Y-%m-%d"))
	context = {'type':'view', 'data':{'label': dtq.strftime("%A %-d %B"), 'id': dsq, 'next': dsn, 'events': events}}
	return render(request, 'viewer/pages/timeline_event.html', context)

def onthisday(request, format='html'):
	logger.info("On This Day requested")
	key = 'onthisday_' + datetime.date.today().strftime("%Y%m%d")
	data = cache.get(key)
	if data is None:
		logger.debug("Generating On This Day")
		data = generate_onthisday()
		if len(data) == 0:
			return render(request, 'viewer/pages/setup.html', {})
		cache.set(key, data, timeout=86400)
		logger.debug("On This Day generated")
	else:
		logger.debug("Getting cached On This Day")
	context = {'type':'view', 'data':data}
	return render(request, 'viewer/pages/onthisday.html', context)
