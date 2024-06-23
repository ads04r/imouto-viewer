from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from viewer.models import Event, Year
from viewer.functions.rdf import rdf_serialize

import logging
logger = logging.getLogger(__name__)

def event_rdf(request, eid):
	data = get_object_or_404(Event, id=eid)
	rdf = rdf_serialize(data, format='pretty-xml')
	if rdf:
		response = HttpResponse(rdf, content_type='application/rdf+xml')
		return response
	raise Http404()

def event_ttl(request, eid):
	data = get_object_or_404(Event, id=eid)
	rdf = rdf_serialize(data, format='turtle')
	if rdf:
		response = HttpResponse(rdf, content_type='application/turtle')
		return response
	raise Http404()

def year_rdf(request, ds):
	data = get_object_or_404(Year, year=ds)
	rdf = rdf_serialize(data, format='pretty-xml')
	if rdf:
		response = HttpResponse(rdf, content_type='application/rdf+xml')
		return response
	raise Http404()

def year_ttl(request, ds):
	data = get_object_or_404(Year, year=ds)
	rdf = rdf_serialize(data, format='turtle')
	if rdf:
		response = HttpResponse(rdf, content_type='application/turtle')
		return response
	raise Http404()


