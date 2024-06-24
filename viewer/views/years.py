from django.http import HttpResponse, Http404, FileResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from background_task.models import Task

from viewer.models import Year, create_or_get_year
from viewer.tasks.reports import generate_report, generate_report_pdf

import os, json

import logging
logger = logging.getLogger(__name__)

def year(request, ds):

	if len(ds) != 4:
		raise Http404()
	y = int(ds)
	obj = create_or_get_year(y)

	if request.method == 'POST':
		data = {}
		year = int(request.POST['createreportyear'])
		title = request.POST['createreporttitle']
		if obj.year != year:
			raise Http404
		obj.caption = title
		obj.save(update_fields=['caption'])
		generate_report_pdf(year)
		return HttpResponseRedirect('../#year_' + str(year))

	context = {'type':'view', 'caption': str(obj), 'year': obj}
	template = 'viewer/pages/year.html'
	if obj.this_year:
		template = 'viewer/pages/this_year.html'
		context['years'] = Year.objects.all()
	else:
		if obj.report_prc == 0:
			active_task = None
			for task in Task.objects.filter(task_name__contains='generate_report', queue='reports'):
				task_year = json.loads(task.task_params)[0][0]
				if task_year == obj.year:
					active_task = task
			if active_task is None:
				generate_report("", obj.year)
	return render(request, template, context)

def year_wordcloud(request, ds):
	data = get_object_or_404(Year, year=int(ds))
	im = data.wordcloud()
	response = HttpResponse(content_type='image/png')
	im.save(response, "PNG")
	return response

def year_report(request, ds):
	data = get_object_or_404(Year, year=int(ds))
	if os.path.exists(data.cached_pdf.path):
		return FileResponse(open(data.cached_pdf.path, 'rb'))
	raise Http404()

def year_report_status(request, ds):
	data = get_object_or_404(Year, year=int(ds))
	template = 'viewer/cards/report-generate.html'
	context = {'year': data}
	if data.cached_pdf:
		template = 'viewer/cards/report-view.html'
	for task in Task.objects.filter(task_name__contains='generate_report_pdf', queue='reports'):
		task_year = json.loads(task.task_params)[0][0]
		if task_year == data.year:
			template = 'viewer/cards/report-pdf-inprogress.html'
			if not(task.locked_at is None):
				if task.locked_by_pid_running() == False:
					template = 'viewer/cards/report-pdf-stopped.html'
	if data.report_prc < 100:
		template = "viewer/cards/report-inprogress.html"

	return render(request, template, context);

def year_reports_json(request):
	data = []
	for year in Year.objects.order_by('-year'):
		if year.report_prc < 100:
			continue
		item = {'id': year.pk, 'uri': year.uri, 'label': year.caption, 'year': year.year, 'pdf': False}
		if year.cached_pdf:
			if os.path.exists(str(year.cached_pdf.file)):
				item['pdf'] = True
		data.append(item)
	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response
