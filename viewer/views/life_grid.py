from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.core.cache import cache
from django.db.models import F, Count
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import LifePeriod
from viewer.forms import LifePeriodForm

from viewer.functions.utils import generate_life_grid

def life_grid(request):

	if request.method == 'POST':

		cache.delete('dashboard')

		form = LifePeriodForm(request.POST)
		if form.is_valid():

			life_period = form.save(commit=False)
			life_period.colour = ('#' + str("%06x" % random.randint(0, 0xFFFFFF)).upper())
			life_period.save()

			return HttpResponseRedirect('./#life-grid')
		else:
			raise Http404(form.errors)

	dob = settings.USER_DATE_OF_BIRTH
	now = datetime.datetime.now().date()
	while dob.weekday() < 6:
		dob = dob - datetime.timedelta(days=1)
	weeks = int((now - dob).days / 7) + 1
	form = LifePeriodForm()
	context = {'start_date': dob, 'weeks': weeks, 'form': form, 'categories': list(LifePeriod.objects.values('type').annotate(count=Count('type')).order_by('-count')), 'grid': generate_life_grid(dob, weeks)}
	return render(request, 'viewer/pages/life_grid.html', context)

