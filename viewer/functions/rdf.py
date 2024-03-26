from w3lib.html import get_base_url
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from django.shortcuts import get_object_or_404
from django.conf import settings
import json, requests, extruct, datetime

def rdf_make_object_uri(object):

	uri = None
	if not(hasattr(object, 'pk')):
		return uri
	if hasattr(settings, 'RDF_NAMESPACE'):
		uri = URIRef(settings.RDF_NAMESPACE + str(object.__class__.__name__).lower() + '/' + str(object.pk))
	if hasattr(settings, 'USER_RDF_NAMESPACE'):
		uri = URIRef(settings.USER_RDF_NAMESPACE + str(object.__class__.__name__).lower() + '/' + str(object.pk))
	if hasattr(object, 'uri'):
		uri = URIRef(getattr(object, 'uri'))
	return uri

def rdf_serialize(object, format='turtle'):

	uri = None
	types = []
	exclude = []
	if hasattr(settings, 'RDF_NAMESPACE'):
		uri = URIRef(settings.RDF_NAMESPACE + str(object.__class__.__name__).lower() + '/' + str(object.pk))
		types.append(URIRef(settings.RDF_NAMESPACE + str(object.__class__.__name__)))
	if hasattr(settings, 'USER_RDF_NAMESPACE'):
		uri = URIRef(settings.USER_RDF_NAMESPACE + str(object.__class__.__name__).lower() + '/' + str(object.pk))
	if hasattr(object, 'uri'):
		uri = URIRef(getattr(object, 'uri'))
	if hasattr(object, 'rdf_types'):
		for type in getattr(object, 'rdf_types'):
			types.append(type)
	if hasattr(object, 'rdf_exclude'):
		exclude = getattr(object, 'rdf_exclude')
	if uri is None:
		return ""
	g = Graph()
	g.bind('imouto', settings.RDF_NAMESPACE)
	g.add((uri, RDFS.label, Literal(str(object))))
	for type in types:
		g.add((uri, RDF.type, URIRef(type)))
	for field in object._meta.fields:
		if field.name.startswith('cached_'):
			continue
		if field.name in exclude:
			continue
		pred = URIRef(settings.RDF_NAMESPACE + field.name)
		classname = str(field.__class__.__name__)
		try:
			value = field.value_from_object(object)
		except:
			value = None
		if value is None:
			continue
		if isinstance(value, datetime.datetime):
			g.add((uri, pred, Literal(value.strftime('%Y-%m-%dT%H:%M:%S%z'), datatype=XSD.dateTime)))
			continue
		if isinstance(value, datetime.date):
			g.add((uri, pred, Literal(value.strftime('%Y-%m-%d'), datatype=XSD.date)))
			continue
		if classname == 'URLField':
			g.add((uri, pred, URIRef(value)))
			continue
		if classname == 'CharField':
			g.add((uri, pred, Literal(value)))
			continue
		if classname == 'SlugField':
			g.add((uri, pred, Literal(value)))
			continue
		if classname == 'TextField':
			if value:
				g.add((uri, pred, Literal(value)))
			continue
		if classname == 'IntegerField':
			g.add((uri, pred, Literal(value, datatype=XSD.integer)))
			continue
		if classname == 'FloatField':
			g.add((uri, pred, Literal(value, datatype=XSD.float)))
			continue
		if classname == 'BooleanField':
			g.add((uri, pred, Literal(str(value).lower(), datatype=XSD.boolean)))
			continue
		link_uri = rdf_make_object_uri(value)
		if classname == 'ForeignKey':
			value = get_object_or_404(field.related_model, pk=field.value_from_object(object))
			link_uri = rdf_make_object_uri(value)
		if not(link_uri is None):
			print(link_uri)
			g.add((uri, pred, URIRef(link_uri)))
			continue
	for prop in list(object._meta._property_names):
		if prop == 'uri':
			continue
		if prop == 'pk':
			continue
		if prop.startswith('rdf_'):
			continue
		if prop in exclude:
			continue
		try:
			value = getattr(object, prop)
		except:
			value = None
		if value is None:
			continue
		pred = URIRef(settings.RDF_NAMESPACE + prop)
		if value.__class__.__name__ == 'QuerySet':
			for item in value.all():
				link_uri = rdf_make_object_uri(item)
				if not(link_uri is None):
					g.add((uri, pred, URIRef(link_uri)))
			continue
		link_uri = rdf_make_object_uri(value)
		if not(link_uri is None):
			g.add((uri, pred, URIRef(link_uri)))
			continue
		if isinstance(value, datetime.datetime):
			g.add((uri, pred, Literal(value.strftime('%Y-%m-%dT%H:%M:%S%z'), datatype=XSD.dateTime)))
			continue
		if isinstance(value, str):
			g.add((uri, pred, Literal(value)))
			continue
		if isinstance(value, bool):
			g.add((uri, pred, Literal(str(value).lower(), datatype=XSD.boolean)))
			continue
		if isinstance(value, int):
			g.add((uri, pred, Literal(str(value), datatype=XSD.integer)))
			continue

	return(g.serialize(format=format))

def get_wikipedia_abstract(url, lang='en'):

	api_uri = 'http://' + lang + '.wikipedia.org/w/api.php'
	title = url.rstrip('/').split('/')[-1]

	data = requests.get(api_uri, params={'action': 'query', 'format': 'json', 'titles': title, 'prop': 'extracts', 'exintro': True, 'explaintext': True}).json()
	pages = data['query']['pages']
	for kk in pages.keys():
		k = str(kk)
		if 'extract' in pages[k]:
			return pages[k]['extract']

	return ''

def get_webpage_data(url, lang='en'):

	r = requests.get(url, headers={"Accept-Language": lang, "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win94; x64; rv:55.0) Gecko/20100101 Firefox/55.0"})
	ct = 'text/html'
	if 'Content-Type' in r.headers:
		ct = r.headers['Content-Type'].split(';')[0].strip()
	if ct == 'text/html':
		return extruct.extract(r.text, base_url=get_base_url(r.text, r.url))
	if ct == 'application/json':
		return {'json-ld': json.loads(r.text)}
	g = Graph()
	if ct == 'application/rdf+turtle':
		g.parse(data=r.text, format='n3')
	if ct == 'application/turtle':
		g.parse(data=r.text, format='n3')
	if ct == 'application/rdf+xml':
		g.parse(data=r.text, format='xml')
	if ct == 'application/rdf+n3':
		g.parse(data=r.text, format='n3')
	return {'json-ld': json.loads(g.serialize(format='json-ld'))}

def wikidata_to_wikipedia(wdid):

	data = get_webpage_data("https://wikidata.org/entity/" + wdid)
	try:
		return data['json-ld']['entities'][wdid]['sitelinks']['enwiki']['url']
	except:
		return ''

def uris_of_type(g, type_uris):

	if(isinstance(type_uris, list)):
		types = type_uris
	else:
		types = [type_uris]
	ret = []
	for type_uri in types:
		for s, p, o in g.triples((None, RDF.type, URIRef(type_uri))):
			if s in ret:
				continue
			ret.append(s)

	return ret

def flatten_rdf_resource(uri, g, lang='en'):

	item = {}
	for s, p, o in g.triples((uri, None, None)):
		if isinstance(o, Literal):
			if not(o.language is None):
				if not(o.language == lang):
					continue
		parse = str(p).replace('#', '/').split('/')
		p_string = parse[-1].lower()
		if len(p_string) > 0:
			if not(p_string in item):
				item[p_string] = []
			o_val = str(o)
			if not(o_val in item[p_string]):
				item[p_string].append(o_val)
	return item

def get_rdf_people(g):

	data = []
	for uri in uris_of_type(g, ['http://schema.org/Person', 'http://dbpedia.org/ontology/Person', 'http://dbpedia.org/class/yago/Person100007846', 'http://xmlns.com/foaf/0.1/Person']):
		item = flatten_rdf_resource(uri, g)
		if len(item) > 0:
			item['type'] = 'Person'
			data.append(item)
	return data

def get_rdf_places(g):

	data = []
	for uri in uris_of_type(g, ['http://dbpedia.org/class/yago/Location100027167', 'http://dbpedia.org/class/yago/Region108630039', 'http://www.w3.org/2003/01/geo/wgs84_pos#SpatialThing', 'http://schema.org/Place', 'http://schema.org/Accommodation', 'http://schema.org/Apartment', 'http://schema.org/CampingPitch', 'http://schema.org/House', 'http://schema.org/SingleFamilyResidence', 'http://schema.org/Room', 'http://schema.org/HotelRoom', 'http://schema.org/MeetingRoom', 'http://schema.org/Suite', 'http://schema.org/AdministrativeArea', 'http://schema.org/City', 'http://schema.org/Country', 'http://schema.org/SchoolDistrict', 'http://schema.org/State', 'http://schema.org/CivicStructure', 'http://schema.org/Airport', 'http://schema.org/Aquarium', 'http://schema.org/Beach', 'http://schema.org/BoatTerminal', 'http://schema.org/Bridge', 'http://schema.org/BusStation', 'http://schema.org/BusStop', 'http://schema.org/Campground', 'http://schema.org/Cemetery', 'http://schema.org/Crematorium', 'http://schema.org/EducationalOrganization', 'http://schema.org/EventVenue', 'http://schema.org/FireStation', 'http://schema.org/GovernmentBuilding', 'http://schema.org/CityHall', 'http://schema.org/Courthouse', 'http://schema.org/DefenceEstablishment', 'http://schema.org/Embassy', 'http://schema.org/LegislativeBuilding', 'http://schema.org/Hospital', 'http://schema.org/MovieTheater', 'http://schema.org/Museum', 'http://schema.org/MusicVenue', 'http://schema.org/Park', 'http://schema.org/ParkingFacility', 'http://schema.org/PerformingArtsTheater', 'http://schema.org/PlaceOfWorship', 'http://schema.org/BuddhistTemple', 'http://schema.org/Church', 'http://schema.org/HinduTemple', 'http://schema.org/Mosque', 'http://schema.org/Synagogue', 'http://schema.org/Playground', 'http://schema.org/PoliceStation', 'http://schema.org/PublicToilet', 'http://schema.org/RVPark', 'http://schema.org/StadiumOrArena', 'http://schema.org/SubwayStation', 'http://schema.org/TaxiStand', 'http://schema.org/TrainStation', 'http://schema.org/Zoo', 'http://schema.org/Landform', 'http://schema.org/BodyOfWater', 'http://schema.org/Canal', 'http://schema.org/LakeBodyOfWater', 'http://schema.org/OceanBodyOfWater', 'http://schema.org/Pond', 'http://schema.org/Reservoir', 'http://schema.org/RiverBodyOfWater', 'http://schema.org/SeaBodyOfWater', 'http://schema.org/Waterfall', 'http://schema.org/Continent', 'http://schema.org/Mountain', 'http://schema.org/Volcano', 'http://schema.org/LandmarksOrHistoricalBuildings', 'http://schema.org/LocalBusiness', 'http://schema.org/Residence', 'http://schema.org/ApartmentComplex', 'http://schema.org/GatedResidenceCommunity', 'http://schema.org/TouristAttraction', 'http://schema.org/TouristDestination']):
		item = flatten_rdf_resource(uri, g)
		loc = {}
		if len(item) > 0:
			loc['lat'] = None
			loc['lon'] = None
			loc['label'] = None
			if 'lat' in item:
				loc['lat'] = item['lat']
			if 'latitude' in item:
				loc['lat'] = item['latitude']
			if 'lon' in item:
				loc['lon'] = item['lon']
			if 'long' in item:
				loc['lon'] = item['long']
			if 'longitude' in item:
				loc['lon'] = item['longitude']
			if((loc['lat'] is None) or (loc['lon'] is None)):
				continue
			if 'name' in item:
				loc['label'] = item['name']
			loc['type'] = 'Location'
			loc['uid'] = ''
			loc['full_label'] = ''
			loc['description'] = ''
			loc['country'] = ''
			loc['address'] = ''
			loc['phone'] = ''
			loc['url'] = ''
			loc['creation_time'] = ''
			loc['destruction_time'] = ''
			loc['wikipedia'] = ''
			loc['image'] = ''
			loc['weather_location'] = ''
			data.append(loc)
	return data

def microdata_to_rdf(data):

	SCHEMA = Namespace("http://schema.org/")
	g = Graph()
	g.bind("schema", SCHEMA)
	if 'rdfa' in data:
		g.parse(data=json.dumps(data['rdfa']), format='json-ld')
	if 'json-ld' in data:
		g.parse(data=json.dumps(data['json-ld']), format='json-ld')

	return g

