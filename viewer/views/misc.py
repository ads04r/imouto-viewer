from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F
from django.conf import settings
from haystack.query import SearchQuerySet
from w3lib.html import get_base_url
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import datetime, pytz, dateutil.parser, json, requests, random, extruct

from viewer.models import Location, Person, Event

def upload_file(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	url = settings.LOCATION_MANAGER_URL + '/import'
	files = {'uploaded_file': request.FILES['uploadformfile']}
	data = {'file_source': request.POST['uploadformfilesource']}

	r = requests.post(url, files=files, data=data)
	return HttpResponseRedirect('./#files')

def locman_import(request):
	url = settings.LOCATION_MANAGER_URL + '/import'
	r = requests.get(url)
	r.raise_for_status()
	response = HttpResponse(r.text, content_type='application/json')
	return response

def locman_process(request):
	url = settings.LOCATION_MANAGER_URL + '/process'
	r = requests.get(url)
	r.raise_for_status()
	response = HttpResponse(r.text, content_type='application/json')
	return response

def importer(request):
	url = settings.LOCATION_MANAGER_URL + '/import'
	r = requests.get(url=url)
	context = {'progress': r.json()}
	return render(request, 'viewer/pages/import.html', context)

def webimporter(request):
	context = {'progress': []}
	return render(request, 'viewer/pages/import-web.html', context)

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
	ret = []

	cache_key = 'search_' + url
	try:
		g = cache.get(cache_key)
	except:
		g = None
	if g is None:
		r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win94; x64; rv:55.0) Gecko/20100101 Firefox/55.0"})
		g = Graph()
		data = extruct.extract(r.text, base_url=get_base_url(r.text, r.url))
		if 'json-ld' in data:
			g.parse(data=json.dumps(data['json-ld']), format='json-ld')
		cache.set(cache_key, g, 86400)

	SCHEMA = Namespace("http://schema.org/")
	g.bind("schema", SCHEMA)
	data = []
	place_uris = ['http://schema.org/Place', 'http://schema.org/Accommodation', 'http://schema.org/Apartment', 'http://schema.org/CampingPitch', 'http://schema.org/House', 'http://schema.org/SingleFamilyResidence', 'http://schema.org/Room', 'http://schema.org/HotelRoom', 'http://schema.org/MeetingRoom', 'http://schema.org/Suite', 'http://schema.org/AdministrativeArea', 'http://schema.org/City', 'http://schema.org/Country', 'http://schema.org/SchoolDistrict', 'http://schema.org/State', 'http://schema.org/CivicStructure', 'http://schema.org/Airport', 'http://schema.org/Aquarium', 'http://schema.org/Beach', 'http://schema.org/BoatTerminal', 'http://schema.org/Bridge', 'http://schema.org/BusStation', 'http://schema.org/BusStop', 'http://schema.org/Campground', 'http://schema.org/Cemetery', 'http://schema.org/Crematorium', 'http://schema.org/EducationalOrganization', 'http://schema.org/EventVenue', 'http://schema.org/FireStation', 'http://schema.org/GovernmentBuilding', 'http://schema.org/CityHall', 'http://schema.org/Courthouse', 'http://schema.org/DefenceEstablishment', 'http://schema.org/Embassy', 'http://schema.org/LegislativeBuilding', 'http://schema.org/Hospital', 'http://schema.org/MovieTheater', 'http://schema.org/Museum', 'http://schema.org/MusicVenue', 'http://schema.org/Park', 'http://schema.org/ParkingFacility', 'http://schema.org/PerformingArtsTheater', 'http://schema.org/PlaceOfWorship', 'http://schema.org/BuddhistTemple', 'http://schema.org/Church', 'http://schema.org/HinduTemple', 'http://schema.org/Mosque', 'http://schema.org/Synagogue', 'http://schema.org/Playground', 'http://schema.org/PoliceStation', 'http://schema.org/PublicToilet', 'http://schema.org/RVPark', 'http://schema.org/StadiumOrArena', 'http://schema.org/SubwayStation', 'http://schema.org/TaxiStand', 'http://schema.org/TrainStation', 'http://schema.org/Zoo', 'http://schema.org/Landform', 'http://schema.org/BodyOfWater', 'http://schema.org/Canal', 'http://schema.org/LakeBodyOfWater', 'http://schema.org/OceanBodyOfWater', 'http://schema.org/Pond', 'http://schema.org/Reservoir', 'http://schema.org/RiverBodyOfWater', 'http://schema.org/SeaBodyOfWater', 'http://schema.org/Waterfall', 'http://schema.org/Continent', 'http://schema.org/Mountain', 'http://schema.org/Volcano', 'http://schema.org/LandmarksOrHistoricalBuildings', 'http://schema.org/LocalBusiness', 'http://schema.org/Residence', 'http://schema.org/ApartmentComplex', 'http://schema.org/GatedResidenceCommunity', 'http://schema.org/TouristAttraction', 'http://schema.org/TouristDestination']
	people = []
	places = []
	for s, p, o in g.triples((None, RDF.type, SCHEMA.Person)):
		people.append(s)
	for uri in place_uris:
		for s, p, o in g.triples((None, RDF.type, URIRef(uri))):
			places.append(s)
	for p in people:
		item = {'type': 'Person'}
		for s, p, o in g.triples((p, None, None)):
			if not(isinstance(o, Literal)):
				continue
			parse = str(p).replace('#', '/').split('/')
			p_string = parse[-1]
			if len(p_string) > 0:
				item[p_string] = str(o)
		if len(item) > 0:
			data.append(item)
	for p in places:
		item = {'type': 'Location'}
		for s, p, o in g.triples((p, None, None)):
			if not(isinstance(o, Literal)):
				continue
			parse = str(p).replace('#', '/').split('/')
			p_string = parse[-1]
			if len(p_string) > 0:
				item[p_string] = str(o)
		if len(item) > 0:
			data.append(item)

	response = HttpResponse(json.dumps(data), content_type='application/json')
	return response
