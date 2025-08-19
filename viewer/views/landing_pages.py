from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.core.cache import cache
from django.db.models import Q, F
from django.conf import settings
from django.contrib.auth.decorators import login_required
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Event, create_or_get_day
from viewer.forms import EventForm, QuickEventForm

from viewer.functions.locations import home_location
from viewer.functions.utils import get_timeline_events, generate_dashboard, get_today, imouto_json_serializer

import logging
logger = logging.getLogger(__name__)

@login_required(login_url='/users/login')
def index(request):
	context = {'type':'index', 'data':[], 'today': create_or_get_day(request.user)}
	if context['today']:
		context['today'].yesterday.get_sleep_information() # Pre-cache so we never end up with any part-processed data
	logger.info("HTML frame requested")
	return render(request, 'viewer/index.html', context)

def dashboard(request):
	logger.info("Dashboard requested")
	key = 'dashboard'
	ret = cache.get(key)
	if ret is None:
		logger.debug("Generating dashboard")
		data = generate_dashboard(request.user)
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
	context = {'tiles': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 'max_zoom': 17, 'home': home_location(request.user)}
	if hasattr(settings, 'MAP_TILES'):
		if settings.MAP_TILES != '':
			context['tiles'] = str(settings.MAP_TILES)
	if hasattr(settings, 'MAX_ZOOM'):
		if settings.MAX_ZOOM != '':
			context['max_zoom'] = str(settings.MAX_ZOOM)
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
	events = get_timeline_events(request.user, dtq)

	dtq = events[0].start_time
	dtn = dtq - datetime.timedelta(days=1)
	dsq = dtq.strftime("%Y%m%d")
	dsn = dtn.strftime("%Y%m%d")

	logger.info("Timeline items requested for " + dtq.strftime("%Y-%m-%d"))
	context = {'type':'view', 'data':{'label': dtq.strftime("%A %-d %B"), 'id': dsq, 'next': dsn, 'events': events}}
	return render(request, 'viewer/pages/timeline_event.html', context)

def onthisday(request, format='html'):
	logger.info("On This Day requested")
	data = get_today(request.user)
	context = {'type':'view', 'data':data}
	return render(request, 'viewer/pages/onthisday.html', context)
