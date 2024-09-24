from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.conf import settings
import requests, json

def pbftile(request, z, x, y):
	tiles_url = settings.MAP_TILES.replace('{z}', str(z)).replace('{x}', str(x)).replace('{y}', str(y))
	r = requests.get(tiles_url)
	response = HttpResponse(content=r.content, status=r.status_code, content_type=r.headers['Content-Type'])
	return response
