import datetime, pytz, sys, os
from viewer.models import *
from viewer.functions.locations import nearest_location

def locate_photos_by_exif(since=None, reassign=False):

	ret = 0
	if since is None:
		datecutoff = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=60)
	else:
		datecutoff = since
	if reassign:
		photos = Photo.objects.filter(time__gte=datecutoff).exclude(lat=None).exclude(lon=None)
	else:
		photos = Photo.objects.filter(location=None, time__gte=datecutoff).exclude(lat=None).exclude(lon=None)
	for photo in photos:
		t = photo.time
		if t is None:
			continue
		events = Event.objects.filter(start_time__lte=t, end_time__gte=t)
		if events.count() > 0:
			continue
		loc = nearest_location(photo.lat, photo.lon)
		if loc is None:
			continue
		photo.location = loc
		photo.save()
		ret = ret + 1

	return ret

def bubble_photo_locations(since=None, loc_id=None, reassign=False):

	if since is None:
		datecutoff = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=60)
	else:
		datecutoff = since
	if loc_id is None:
		places = Location.objects.filter(events__start_time__gte=datecutoff).distinct()
	else:
		places = Location.objects.filter(id=loc_id).distinct()
	ret = 0
	for loc in places:
		for event in loc.events.filter(start_time__gte=datecutoff):
			if reassign:
				photos = event.photos().all()
			else:
				photos = event.photos().filter(location=None)
			pc = photos.count()
			if pc == 0:
				continue
			ret = ret + pc
			for photo in photos:
				photo.location = loc
				photo.save()
	return ret
