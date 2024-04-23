from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from viewer.models import Questionnaire, QuestionnaireQuestion, QuestionnaireAnswer, DataReading
from viewer.forms import QuestionnaireForm

import json

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
	context = {'items': Questionnaire.objects.all(), 'form': form}
	template = 'viewer/pages/questionnaires.html'
	return render(request, template, context)

def questionnaireview(request, id):

	data = get_object_or_404(Questionnaire, pk=id)
	context = {'item': data, 'form': None}
	template = 'viewer/pages/questionnaire.html'
	return render(request, template, context)

def questionnaireedit(request, id):

	data = get_object_or_404(Questionnaire, pk=id)
	form = QuestionnaireForm(instance=data)
	context = {'item': data, 'form': form}
	template = 'viewer/pages/questionnaire.html'
	return render(request, template, context)

@csrf_exempt
def questionnairedelete(request, id):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(Questionnaire, pk=id)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response
