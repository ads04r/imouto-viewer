from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.conf import settings

from viewer.models import Month, Day, HistoricalEvent, create_or_get_month
from viewer.tasks.reports import generate_staticmap

import logging
logger = logging.getLogger(__name__)

def month(request, ds):

	if len(ds) != 6:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:])
	logger.info("Month " + ds + " requested")
	obj = create_or_get_month(request.user, m, y)

	history = HistoricalEvent.objects.filter(date__month=m, date__year=y).order_by('date')
	longest_journey = obj.longest_journey
	if not(longest_journey is None):
		generate_staticmap(longest_journey.pk)

	context = {'type':'view', 'caption': str(obj), 'month': obj, 'history': history, 'longest_journey': longest_journey}
	template = 'viewer/pages/month.html'
	if obj.this_month:
		template = 'viewer/pages/this_month.html'
	return render(request, template, context)

