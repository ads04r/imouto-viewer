from w3lib.html import get_base_url
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import json, requests, extruct

def get_webpage_data(url):

	r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win94; x64; rv:55.0) Gecko/20100101 Firefox/55.0"})
	data = extruct.extract(r.text, base_url=get_base_url(r.text, r.url))
	return data

def uris_of_type(g, type_uris):

	if(isinstance(type_uris, list)):
		types = type_uris
	else:
		types = [type_uris]
	ret = []
	for type_uri in types:
		for s, p, o in g.triples((None, RDF.type, URIRef(type_uri))):
			ret.append(s)

	return ret

def get_schema_people(g):

	data = []
	for uri in uris_of_type(g, 'http://schema.org/Person'):

		item = {'type': 'Person'}
		for s, p, o in g.triples((uri, None, None)):
			parse = str(p).replace('#', '/').split('/')
			p_string = parse[-1]
			if len(p_string) > 0:
				item[p_string] = str(o)
		if len(item) > 0:
			data.append(item)

	return data

def get_schema_places(g):

	data = []
	for uri in uris_of_type(g, ['http://schema.org/Place', 'http://schema.org/Accommodation', 'http://schema.org/Apartment', 'http://schema.org/CampingPitch', 'http://schema.org/House', 'http://schema.org/SingleFamilyResidence', 'http://schema.org/Room', 'http://schema.org/HotelRoom', 'http://schema.org/MeetingRoom', 'http://schema.org/Suite', 'http://schema.org/AdministrativeArea', 'http://schema.org/City', 'http://schema.org/Country', 'http://schema.org/SchoolDistrict', 'http://schema.org/State', 'http://schema.org/CivicStructure', 'http://schema.org/Airport', 'http://schema.org/Aquarium', 'http://schema.org/Beach', 'http://schema.org/BoatTerminal', 'http://schema.org/Bridge', 'http://schema.org/BusStation', 'http://schema.org/BusStop', 'http://schema.org/Campground', 'http://schema.org/Cemetery', 'http://schema.org/Crematorium', 'http://schema.org/EducationalOrganization', 'http://schema.org/EventVenue', 'http://schema.org/FireStation', 'http://schema.org/GovernmentBuilding', 'http://schema.org/CityHall', 'http://schema.org/Courthouse', 'http://schema.org/DefenceEstablishment', 'http://schema.org/Embassy', 'http://schema.org/LegislativeBuilding', 'http://schema.org/Hospital', 'http://schema.org/MovieTheater', 'http://schema.org/Museum', 'http://schema.org/MusicVenue', 'http://schema.org/Park', 'http://schema.org/ParkingFacility', 'http://schema.org/PerformingArtsTheater', 'http://schema.org/PlaceOfWorship', 'http://schema.org/BuddhistTemple', 'http://schema.org/Church', 'http://schema.org/HinduTemple', 'http://schema.org/Mosque', 'http://schema.org/Synagogue', 'http://schema.org/Playground', 'http://schema.org/PoliceStation', 'http://schema.org/PublicToilet', 'http://schema.org/RVPark', 'http://schema.org/StadiumOrArena', 'http://schema.org/SubwayStation', 'http://schema.org/TaxiStand', 'http://schema.org/TrainStation', 'http://schema.org/Zoo', 'http://schema.org/Landform', 'http://schema.org/BodyOfWater', 'http://schema.org/Canal', 'http://schema.org/LakeBodyOfWater', 'http://schema.org/OceanBodyOfWater', 'http://schema.org/Pond', 'http://schema.org/Reservoir', 'http://schema.org/RiverBodyOfWater', 'http://schema.org/SeaBodyOfWater', 'http://schema.org/Waterfall', 'http://schema.org/Continent', 'http://schema.org/Mountain', 'http://schema.org/Volcano', 'http://schema.org/LandmarksOrHistoricalBuildings', 'http://schema.org/LocalBusiness', 'http://schema.org/Residence', 'http://schema.org/ApartmentComplex', 'http://schema.org/GatedResidenceCommunity', 'http://schema.org/TouristAttraction', 'http://schema.org/TouristDestination']):

		item = {'type': 'Location'}
		for s, p, o in g.triples((uri, None, None)):
			parse = str(p).replace('#', '/').split('/')
			p_string = parse[-1]
			if len(p_string) > 0:
				item[p_string] = str(o)
		if len(item) > 0:
			data.append(item)

	return data

def microdata_to_rdf(data):

	SCHEMA = Namespace("http://schema.org/")
	g = Graph()
	g.bind("schema", SCHEMA)
	if 'json-ld' in data:
		g.parse(data=json.dumps(data['json-ld']), format='json-ld')

	return g

