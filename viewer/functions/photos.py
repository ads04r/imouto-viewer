import datetime, pytz, random, os
from django.conf import settings
from viewer.models import Photo, Event, Location
from viewer.functions.locations import nearest_location
from PIL import Image, ImageDraw
from math import sin, cos, pi
from libxmp import XMPMeta

import logging
logger = logging.getLogger(__name__)

def get_year_sample_photos(year, max=50):

	photos = []
	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)
	for photo in Photo.objects.filter(time__lte=dte, time__gte=dts, face_count__gt=0).order_by('-face_count')[0:max]:
		photos.append(photo)
	for photo in Photo.objects.filter(time__lte=dte, time__gte=dts, face_count=0)[0:max]:
		photos.append(photo)
	random.shuffle(photos)

	ret = []
	for photo in photos[0:max]:
		ret.append(photo.thumbnail(640))
	return ret

def hexagon_crop(im, landscape=True):

	w = float(im.width) / 2
	h = float(im.height) / 2
	shape = ()
	for i in range(0, 6):
		if landscape:
			t = (float(i) + 0.5) * (pi / 3.0)
		else:
			t = float(i) * (pi / 3.0)
		shape = shape + (((w + (sin(t) * w), h + (cos(t) * h))))

	mask = Image.new('RGBA', im.size)
	d = ImageDraw.Draw(mask)
	d.polygon(shape, fill='#000')
	ret = Image.new('RGBA', im.size)
	ret.paste(im, (0, 0), mask)
	return ret

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

def get_untagged_photo_ids():

	return [photo.pk for photo in Photo.objects.filter(time__gt=Photo.objects.exclude(tags=None).order_by('-time').first().time)]

def get_xmp_sidecar_tags(photo_id):

	try:
		photo = Photo.objects.get(pk=photo_id)
	except:
		return []
	xmp_path = photo.file.path + '.xmp'
	if not os.path.exists(xmp_path):
		ext_len = len(photo.file.path.split('.')[-1])
		xmp_path = photo.file.path[:-ext_len] + 'xmp'
	if not os.path.exists(xmp_path):
		return []
	xmp = XMPMeta()
	with open(xmp_path, 'r') as fp:
		xmp.parse_from_str(fp.read())
	ret = []
	for tag in [xmp.get_array_item("http://purl.org/dc/elements/1.1/", 'subject', (i + 1)) for i in range(0, xmp.count_array_items("http://purl.org/dc/elements/1.1/", 'subject'))]:
		if tag == '':
			continue
		photo.tag(tag)
		ret.append(tag)

	return ret
