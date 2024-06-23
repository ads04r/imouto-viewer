import datetime, pytz, random, sys, requests, os
from viewer.models import *
from django.conf import settings
from dateutil import parser

import logging
logger = logging.getLogger(__name__)

def get_moonshine_artist_image(mbid):

	if not(hasattr(settings, 'MOONSHINE_URL')):
		return None
	if not(hasattr(settings, 'MEDIA_ROOT')):
		return None

	filename = mbid.replace('-', '').lower() + '.jpg'
	images_path = os.path.join(settings.MEDIA_ROOT, 'artist_images', filename[0])
	try:
		os.makedirs(images_path)
	except:
		pass
	if not os.path.exists(images_path):
		return None

	ret = os.path.join(images_path, filename)
	if os.path.exists(ret):
		return ret

	url = settings.MOONSHINE_URL + '/artist/' + mbid
	r = requests.get(url)
	artist_info = r.json()
	if not isinstance(artist_info, (dict)):
		return None
	if not 'images' in artist_info:
		return None
	images = artist_info['images']
	random.shuffle(images)
	for image_url in images:
		r = requests.get(image_url)
		im = Image.open(BytesIO(r.content))
		bbox = im.getbbox()
		w = bbox[2]
		h = bbox[3]
		if h > w:
			im = im.crop((0, 0, w, w))
		else:
			x = int((w - h) / 2)
			im = im.crop((x, 0, x + h, h))
		im.save(ret, quality=95)
		if os.path.exists(ret):
			if os.path.getsize(ret) > 4:
				return ret
			os.remove(ret)

	return None

def get_moonshine_tracks(start_time, end_time):

	if not(hasattr(settings, 'MOONSHINE_URL')):
		return []

	dt = datetime.date(start_time.year, start_time.month, 1)
	ret = []
	while dt < end_time.date():
		url = settings.MOONSHINE_URL + '/time/' + dt.strftime("%Y-%m")
		r = requests.get(url)
		for item in r.json():
			if not('time' in item):
				continue
			item['time'] = parser.parse(item['time'])
			if item['time'] < start_time:
				continue
			if item['time'] > end_time:
				continue
			item['type'] = 'music_track'
			ret.append(item)
		dtd = dt.day
		dt = (dt + datetime.timedelta(days=32)).replace(day=dtd) # Add a calendar month
	return ret

