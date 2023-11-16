from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random, os

from viewer.models import Event, LifeReport, LifeReportGraph
from viewer.forms import CreateReportForm
from viewer.tasks.reports import generate_report

from viewer.functions.utils import get_report_queue

def reports(request):
	if request.method == 'POST':
		form = CreateReportForm(request.POST)
		if form.is_valid():
			year = int(request.POST['year'])
			title = str(request.POST['label'])
			style = str(request.POST['style'])
			options = {}
			options['reportdetail'] = request.POST['reportdetail']
			options['peoplestats'] = False
			options['wordcloud'] = False
			options['maps'] = False
			if 'peoplestats' in request.POST:
				if request.POST['peoplestats'] == 'on':
					options['peoplestats'] = True
			if 'wordcloud' in request.POST:
				if request.POST['wordcloud'] == 'on':
					options['wordcloud'] = True
			if 'maps' in request.POST:
				if request.POST['maps'] == 'on':
					options['maps'] = True
			generate_report(title, year, options, style)
			return HttpResponseRedirect('./#reports')
		else:
			raise Http404(form.errors)

	form = CreateReportForm()
	data = []
	completed_years = []
	for report in LifeReport.objects.all().order_by('-modified_date').values('id', 'label', 'year', 'pdf'):
		item = {'id': report['id'], 'pk': report['id'], 'year': report['year'], 'label': report['label'], 'pdf': False}
		completed_years.append(report['year'])
		if report['pdf']:
			if os.path.exists(report['pdf']):
				item['pdf'] = True
		data.append(item)
	context = {'type':'view', 'data':data, 'form': form, 'settings': {}, 'years': []}
	y1 = Event.objects.all().order_by('start_time')[0].start_time.year + 1
	y2 = Event.objects.all().order_by('-start_time')[0].start_time.year - 1
	for y in range(y2, y1 - 1, -1):
		if not(y in completed_years):
			context['years'].append(y)
	if hasattr(settings, 'MOONSHINE_URL'):
		if settings.MOONSHINE_URL != '':
			context['settings']['moonshine_url'] = settings.MOONSHINE_URL
	return render(request, 'viewer/pages/reports.html', context)

def reports_json(request):
	data = []
	for report in LifeReport.objects.all():
		item = {'id': report.id, 'label': report.label, 'year': report.year, 'pdf': False, 'style': report.style, 'options': json.loads(report.options)}
		if report.pdf:
			if os.path.exists(report.pdf.path):
				item['pdf'] = True
		data.append(item)
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def report(request, id, page='misc'):
	data = get_object_or_404(LifeReport, id=id)
	context = {'type':'report', 'data':data, 'page':page}
	if context['page'] == 'misc':
		context['page'] = ''
	return render(request, 'viewer/pages/report.html', context)

def report_graph(request, id):
	data = get_object_or_404(LifeReportGraph, id=id)
	im = data.image()
	response = HttpResponse(content_type='image/png')
	im.save(response, "PNG")
	return response

def report_pdf(request, id):
	data = get_object_or_404(LifeReport, id=id)
	pdf = open(data.pdf.path, 'rb')
	response = HttpResponse(content=pdf)
	response['Content-Type'] = 'application/pdf'
	response['Content-Disposition'] = 'attachment; filename="%s.pdf"' % str(data)
	return response

def report_json(request, id):
	data = get_object_or_404(LifeReport, id=id)
	ret = data.to_dict()
	ret['pages'] = data.pages()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

def report_queue(request):
	data = get_report_queue()
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response

def report_words(request, id):
	data = get_object_or_404(LifeReport, id=id)
	txt = data.words()
	response = HttpResponse(content=txt, content_type='text/plain')
	return response

def report_wordcloud(request, id):
	data = get_object_or_404(LifeReport, id=id)
	im = data.wordcloud()
	response = HttpResponse(content_type='image/png')
	im.save(response, "PNG")
	return response

@csrf_exempt
def reportdelete(request, rid):
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(LifeReport, pk=rid)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response
