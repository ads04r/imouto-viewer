from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.conf import settings

from viewer.models import Month, Day, HistoricalEvent, create_or_get_month

def month(request, ds):

	if len(ds) != 6:
		raise Http404()
	y = int(ds[0:4])
	m = int(ds[4:])
	obj = create_or_get_month(m, y)

	history = HistoricalEvent.objects.filter(date__month=m, date__year=y).order_by('date')

	context = {'type':'view', 'caption': str(obj), 'month': obj, 'history': history}
	return render(request, 'viewer/pages/month.html', context)

