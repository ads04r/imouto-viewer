from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.conf import settings

from viewer.models import Year, create_or_get_year

def year(request, ds):

	if len(ds) != 4:
		raise Http404()
	y = int(ds)
	obj = create_or_get_year(y)

	context = {'type':'view', 'caption': str(obj), 'year': obj}
	template = 'viewer/pages/year.html'
	if obj.this_year:
		template = 'viewer/pages/this_year.html'
		context['years'] = Year.objects.all()
	return render(request, template, context)

def year_wordcloud(request, ds):
	data = get_object_or_404(Year, year=int(ds))
	im = data.wordcloud()
	response = HttpResponse(content_type='image/png')
	im.save(response, "PNG")
	return response
