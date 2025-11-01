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
from viewer.functions.utils import get_timeline_events, get_today, imouto_json_serializer, first_event_time
from viewer.functions.dashboard import Dashboard

import logging
logger = logging.getLogger(__name__)

def dashboard(request):
	logger.info("Dashboard requested")
	context = {}
	ret = render(request, 'viewer/pages/dashboard.html', context)
	return ret

def dashboard_json(request):
	data = {}
	response = HttpResponse(json.dumps(data, default=imouto_json_serializer), content_type='application/json')
	return response

def dashboard_panel(request, id):
	context = {'dashboard': Dashboard(request.user)}
#	try:
	ret = render(request, 'viewer/dashboard/' + id + '.html', context)
#	except:
#		raise Http404()
	return ret
