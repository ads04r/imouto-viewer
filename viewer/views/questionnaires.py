from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from viewer.models import Questionnaire, QuestionnaireQuestion, QuestionnaireAnswer, DataReading
from viewer.forms import QuestionnaireForm, QuestionForm

import json, datetime, pytz

import logging
logger = logging.getLogger(__name__)

def questionnaires(request):

	if request.method == 'POST':
		cache.delete('dashboard')
		form = QuestionnaireForm(request.POST)
		if form.is_valid():
			q = form.save(commit=False)
			q.save()
			return HttpResponseRedirect('./#questionnaire_' + str(q.id))
		raise Http404(form.errors)

	form = QuestionnaireForm()
	context = {'items': Questionnaire.objects.filter(user=request.user), 'form': form}
	template = 'viewer/pages/questionnaires.html'
	return render(request, template, context)

def questionnaireview(request, id):

	data = get_object_or_404(Questionnaire, pk=id)
	now = pytz.utc.localize(datetime.datetime.utcnow())

	if request.method == 'POST':
		cache.delete('dashboard')
		result = data.parse_request(request.POST)
		if 'status' in result:
			if result['status']:
				for kk in result['results'].keys():
					k = str(kk)
					v = result['results'][k]
					try:
						item = DataReading(user=request.user, start_time=now, end_time=now, type=k, value=v)
						item.save()
					except:
						item = None
				if not(item is None):
					data.last_taken = now
					data.save(update_fields=['last_taken'])
					return HttpResponseRedirect('../#questionnaires')
		raise Http404("Invalid form data.")

	context = {'item': data, 'form': None}
	template = 'viewer/pages/questionnaire.html'
	return render(request, template, context)

