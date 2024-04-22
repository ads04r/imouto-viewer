from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.conf import settings

from viewer.models import Questionnaire, QuestionnaireQuestion, QuestionnaireAnswer, DataReading
from viewer.forms import QuestionnaireForm

def questionnaires(request):

	form = QuestionnaireForm()
	context = {'items': Questionnaire.objects.all(), 'form': form}
	template = 'viewer/pages/questionnaires.html'
	return render(request, template, context)

