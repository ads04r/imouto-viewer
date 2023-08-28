from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import F
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Photo, Event

@csrf_exempt
def photo_json(request, uid):
	if request.method == 'POST':
		caption = request.POST['image_caption']
		pid = request.POST['photo_id']
		eid = request.POST['event_id']
		cache_key = 'event_' + str(eid)
		set_cover = False
		if 'event_cover_image' in request.POST:
			if request.POST['event_cover_image'] == 'on':
				set_cover = True
		if uid != pid:
			raise Http404()
		photo = get_object_or_404(Photo, pk=pid)
		event = get_object_or_404(Event, pk=eid)
		if set_cover:
			event.cover_photo = photo
		else:
			if event.cover_photo == photo:
				event.cover_photo = None
		event.save()
		event.auto_tag()
		photo.caption = caption
		photo.save()
		cache.delete(cache_key)
		return HttpResponseRedirect('../#event_' + str(eid))
	data = get_object_or_404(Photo, pk=uid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def photo_full(request, uid):
	data = get_object_or_404(Photo, pk=uid)
	im = data.image()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def photo_thumbnail(request, uid):
	data = get_object_or_404(Photo, pk=uid)
	im = data.thumbnail(200)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response
