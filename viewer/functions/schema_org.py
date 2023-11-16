from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from viewer.models import LocationCategory, SchemaOrgClass
from viewer.functions.rdf import uris_of_type
import requests

def import_schema_org(url="https://schema.org/version/latest/schemaorg-current-https.ttl", lang='en'):

	r = requests.get(url, headers={"Accept-Language": lang, "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win94; x64; rv:55.0) Gecko/20100101 Firefox/55.0"})
	g = Graph()
	g.parse(data=r.text, format='n3')

	for uri in uris_of_type(g, RDFS.Class):
		label = ''
		comment = ''
		for s, p, o in g.triples((URIRef(uri), None, None)):
			if str(p) == 'http://www.w3.org/2000/01/rdf-schema#label':
				label = str(o)
			if str(p) == 'http://www.w3.org/2000/01/rdf-schema#comment':
				comment = str(o)
		if label == '':
			continue
		try:
			item = SchemaOrgClass.objects.get(uri=uri)
		except:
			item = SchemaOrgClass(uri=uri)
		item.label = label
		item.comment = comment
		item.save()

	for s, p, o in g.triples((None, RDFS.subClassOf, None)):
		child_uri = str(s)
		parent_uri = str(o)
		try:
			child_item = SchemaOrgClass.objects.get(uri=child_uri)
		except:
			child_item = None
		if child_item is None:
			continue
		try:
			parent_item = SchemaOrgClass.objects.get(uri=parent_uri)
		except:
			parent_item = None
		if parent_item is None:
			continue
		child_item.parent = parent_item
		child_item.save(update_fields=['parent'])

def match_categories():

	LocationCategory.objects.filter(caption='').delete()

	for lc in LocationCategory.objects.filter(schema_map=None):

		for sc in SchemaOrgClass.objects.filter(label__iexact=lc.caption):
			lc.schema_map = sc

		lc.save(update_fields=['schema_map'])
