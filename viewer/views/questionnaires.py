from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from viewer.models import Questionnaire, QuestionnaireQuestion, QuestionnaireAnswer, DataReading
from viewer.forms import QuestionnaireForm, QuestionForm

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

	if request.method == 'POST':
		cache.delete('dashboard')
		form = QuestionForm(request.POST)
		if form.is_valid():
			q = form.save(commit=False)
			q.save()
			return HttpResponseRedirect('./#questionnaire_' + str(id))
		raise Http404(form.errors)

	data = get_object_or_404(Questionnaire, pk=id)
	form = QuestionForm()
	context = {'item': data, 'form': form, 'options': list(DataReading.objects.order_by().values_list('type', flat=True).distinct())}
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

@csrf_exempt
def questiondelete(request, id):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(Question, pk=id)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response
