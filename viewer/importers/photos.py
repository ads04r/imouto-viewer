import django, datetime, pytz, os, exifread, requests
from django.conf import settings
from django.db.models import Q
from django.core.files import File
from django.core.cache import cache

from viewer.models import Photo
from viewer.functions.people import find_person_by_picasaid as find_person
from viewer.functions.geo import convert_to_degrees
from viewer.functions.location_manager import get_logged_position

import logging
logger = logging.getLogger(__name__)

def import_photo_file(filepath, tzinfo=pytz.UTC):
	"""
	Imports a photo into the lifelog data as a Photo object. During import, the function attempts to
	annotate the photo based on EXIF data, and existing data within Imouto if available.

	:param filepath: The path of the photo to import.
	:param tzinfo: A pytz timezone object relating to the timezone in which the photo was taken, as older cameras (such as mine!) don't store this information.
	:return: Returns the new Photo object created by the function call.
	:rtype: Photo
	"""
	path = os.path.abspath(filepath)

	try:
		photo = Photo.objects.get(file=path)
	except:
		photo = Photo(file=path)
		photo.save()

	exif = exifread.process_file(open(path, 'rb'))

	if 'Image DateTime' in exif:
		dsa = str(exif['Image DateTime']).replace(' ', ':').split(':')
		try:
			dt = tzinfo.localize(datetime.datetime(int(dsa[0]), int(dsa[1]), int(dsa[2]), int(dsa[3]), int(dsa[4]), int(dsa[5])))
		except:
			dt = tzinfo.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(path)))
		photo.time = dt.astimezone(pytz.UTC)
		photo.save()

	if 'EXIF DateTimeOriginal' in exif:
		dsa = str(exif['EXIF DateTimeOriginal']).replace(' ', ':').split(':')
		try:
			dt = tzinfo.localize(datetime.datetime(int(dsa[0]), int(dsa[1]), int(dsa[2]), int(dsa[3]), int(dsa[4]), int(dsa[5])))
		except:
			dt = tzinfo.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(path)))
		photo.time = dt.astimezone(pytz.UTC)
		photo.save()

	if (('GPS GPSLatitude' in exif) & ('GPS GPSLongitude' in exif)):
		latdms = exif['GPS GPSLatitude']
		londms = exif['GPS GPSLongitude']
		latr = str(exif['GPS GPSLatitudeRef']).lower()
		lonr = str(exif['GPS GPSLongitudeRef']).lower()
		lat = convert_to_degrees(latdms)
		if latr == 's':
			lat = 0 - lat
		lon = convert_to_degrees(londms)
		if lonr == 'w':
			lon = 0 - lon
		if((lat != 0.0) or (lon != 0.0)):
			photo.lat = lat
			photo.lon = lon
			photo.save()
	else:
		if photo:
			if photo.time:
				dt = photo.time
				lat, lon = get_logged_position(dt)
				if not(lat is None):
					photo.lat = lat
					photo.lon = lon
					photo.save()

	return photo

def import_picasa_faces(picasafile):
	"""
	Tags the photos within Imouto Viewer with person data from Google Picasa. Takes a Picasa sidecar file,
	attempts to match it up with photos and people already in Imouto Viewer, and links them accordingly.

	:param picasafile: The path of the Picasa sidecar file from which to read.
	:return: The number of new tags created.
	:rtype: int
	"""
	contacts = {}
	faces = {}
	path = os.path.dirname(picasafile)
	full_path = os.path.abspath(path)
	ret = 0
	if os.path.exists(picasafile):
		lf = ''
		with open(picasafile) as f:
			lines = f.readlines()
		for liner in lines:
			line = liner.strip()
			if line == '':
				continue
			if ((line[0] == '[') & (line[-1:] == ']')):
				lf = line.lstrip('[').rstrip(']')
			if lf == 'Contacts2':
				parse = line.replace(';', '').split('=')
				if len(parse) == 2:
					contacts[parse[0]] = find_person(parse[0], parse[1])
			if ((line[0:6] == 'faces=') & (lf != '')):
				item = []
				for segment in line[6:].split(';'):
					structure = segment.split(',')
					if not(lf in faces):
						faces[lf] = []
					faces[lf].append(structure[1])

	for filename in faces.keys():
		if len(filename) == 0:
			continue
		full_filename = os.path.join(full_path, filename)
		if not(os.path.isfile(full_filename)):
			continue
		try:
			photo = Photo.objects.get(file=full_filename)
		except:
			photo = None
		if photo is None:
			continue
		for file_face in faces[filename]:
			if not(file_face in contacts):
				contacts[file_face] = find_person(file_face)
			person = contacts[file_face]
			if person is None:
				continue
			if person in photo.people.all():
				continue
			photo.people.add(person)
			ret = ret + 1
			for event in photo.events().all():
				event.people.add(person)
	return ret

def import_photo_directory(path, tzinfo=pytz.UTC):
	"""
	Scans a local directory for photos and calls import_photo_file for every photo file found. If it
	finds a Picasa sidecar file, it imports that too by calling import_picasa_faces.

	:param filepath: The path of the directory to scan.
	:param tzinfo: A pytz timezone object relating to the timezone in which the photos were taken, as older cameras (such as mine!) don't store this information.
	:return: A list of the new Photo objects created with this function call.
	:rtype: list
	"""
	full_path = os.path.abspath(path)
	ret = []

	picasafile = os.path.join(full_path, '.picasa.ini')
	if(not(os.path.exists(picasafile))):
		picasafile = os.path.join(full_path, 'picasa.ini')
	if(not(os.path.exists(picasafile))):
		picasafile = os.path.join(full_path, 'Picasa.ini')

	photos = []
	for f in os.listdir(full_path):
		if not(f.lower().endswith('.jpg')):
			continue
		photo_file = os.path.join(full_path, f)
		try:
			photo = Photo.objects.get(file=photo_file)
		except:
			photo = None
			photos.append(photo_file)

	for photo in photos:
		p = import_photo_file(photo, tzinfo)
		if p is None:
			continue
		ret.append(photo)

	faces = import_picasa_faces(picasafile)

	gps_data = []
	for photo_path in ret:
		try:
			photo = Photo.objects.get(file=photo_path)
		except:
			photo is None
		if not(photo is None):
			if photo.time:
				if photo.lat:
					if photo.lon:
						ds = photo.time.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
						lat = str(photo.lat)
						lon = str(photo.lon)
						gps_data.append([ds, lat, lon])
	if len(gps_data) > 0:
		op = ''
		for row in gps_data:
			op = op + '\t'.join(row) + '\n'

		url = settings.LOCATION_MANAGER_URL + '/import'
		files = {'uploaded_file': op}
		data = {'file_source': 'photo', 'file_format': 'csv'}

		r = requests.post(url, files=files, data=data)
		st = r.status_code

	return ret

