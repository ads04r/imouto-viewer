from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F
from django.conf import settings
from haystack.query import SearchQuerySet
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Location, Person, Event, WatchedDirectory
from viewer.functions.rdf import get_webpage_data, microdata_to_rdf, get_rdf_people, get_rdf_places
from viewer.functions.location_manager import get_location_manager_import_queue, get_location_manager_process_queue
from viewer.forms import WatchedDirectoryForm

def upload_file(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	url = settings.LOCATION_MANAGER_URL + '/import'
	files = {'uploaded_file': request.FILES['uploadformfile']}
	data = {'file_source': request.POST['uploadformfilesource']}

	r = requests.post(url, files=files, data=data)
	r.raise_for_status()
	return HttpResponseRedirect('./#files')

def locman_import(request):
	response = HttpResponse(json.dumps(get_location_manager_import_queue()), content_type='application/json')
	return response

def locman_process(request):
	response = HttpResponse(json.dumps(get_location_manager_process_queue()), content_type='application/json')
	return response

def importer(request):
	context = {'progress': get_location_manager_import_queue(), 'form': WatchedDirectoryForm(), 'paths': WatchedDirectory.objects.all()}
	return render(request, 'viewer/pages/import.html', context)

def webimporter(request):
	context = {'progress': []}
	return render(request, 'viewer/pages/import-web.html', context)

def watcheddir(request, uid=None):
	if request.method == 'POST':
		response = HttpResponse(json.dumps(request.POST), content_type='application/json')
		return response
	data = get_object_or_404(WatchedDirectory, pk=uid)
	context = {'data': data, 'form': WatchedDirectoryForm(instance=data)}
	return render(request, 'viewer/pages/watched_dir.html', context)

@csrf_exempt
def search(request):
	if request.method != 'POST':
		raise Http404()
	data = json.loads(request.body)
	query = data['query']
	ret = []

	cache_key = 'search_' + query
	sq = cache.get(cache_key)
	if sq is None:
		sq = SearchQuerySet().filter(content=query).order_by('-start_time')[0:50]
		cache.set(cache_key, sq, 86400)

	for searchresult in sq:
		event = searchresult.object
		if event is None:
			continue
		description = event.description[0:50]
		if len(description) == 50:
			description = description[0:(description.rfind(' '))]
			if len(description) > 0:
				description = description + ' ...'
		if description == '':
			description = event.start_time.strftime("%a %-d %b %Y")
		item = {'label': event.caption, 'id': event.id, 'description': description, 'date': event.start_time.strftime("%A %-d %B"), 'type': event.type, 'link': 'event_' + str(event.id)}
		ret.append(item)
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

@csrf_exempt
def parse_rdf(request):
	if request.method != 'POST':
		raise Http404()
	query = json.loads(request.body)
	url = query['url']
	if 'wikipedia.org/wiki/' in url:
		p = url.strip('/').split('/')
		url = 'https://dbpedia.org/data/' + p[-1] + '.rdf'
	ret = []

	g = None
	cache_key = 'search_' + url
	try:
		g = cache.get(cache_key)
	except:
		g = None
	if g is None:
		data = get_webpage_data(url)
		g = microdata_to_rdf(data)
		cache.set(cache_key, g, 86400)

	data = []
	data = data + get_rdf_people(g)
	data = data + get_rdf_places(g)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response
