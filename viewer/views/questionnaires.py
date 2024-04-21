from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.conf import settings

from viewer.models import Questionnaire, QuestionnaireQuestion, QuestionnaireAnswer, DataReading

def questionnaires(request):

	context = {}
	template = 'viewer/pages/questionnaires.html'
	return render(request, template, context)

