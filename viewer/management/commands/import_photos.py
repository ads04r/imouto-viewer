from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_photo_directory, import_picasa_faces
from viewer.functions.photos import bubble_photo_locations, locate_photos_by_exif
import os, sys, pytz

class Command(BaseCommand):
	"""
	Command for importing photos and related information, such as GPS positions and face information.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="photo_path", default="", help="A path to search for photos.")
		parser.add_argument("-z", "--timezone", action="store", dest="tz_info", default="", help="The timezone of the photos, useful for when none is specified in the EXIF data.")
		parser.add_argument("-f", "--update-faces", action="store_true", dest="faces_only", help="If this switch is present, the function doesn't import any new photos, but updates face data from any picasa.ini files present.")

	def handle(self, *args, **kwargs):

		path = kwargs['photo_path']
		tz_string = kwargs['tz_info']
		faces_only = kwargs['faces_only']

		if tz_string == '':
			if settings.TIME_ZONE:
				tz = pytz.timezone(settings.TIME_ZONE)
			else:
				tz = pytz.UTC
		elif tz_string.upper() == 'UTC':
			tz = pytz.UTC
		else:
			tz = pytz.timezone(tz_string)
		if len(path) == 0:
			sys.stderr.write(self.style.ERROR("Invalid path to images; must be specified using the --input argument.\n"))
			sys.exit(1)
		full_path = os.path.abspath(path)
		if not(os.path.isdir(full_path)):
			sys.stderr.write(self.style.ERROR("Path '" + full_path + "' not found.\n"))
			sys.exit(1)

		if faces_only:

			picasafile = os.path.join(full_path, '.picasa.ini')
			if(not(os.path.exists(picasafile))):
				picasafile = os.path.join(full_path, 'picasa.ini')
			if(not(os.path.exists(picasafile))):
				picasafile = os.path.join(full_path, 'Picasa.ini')

			ret = 0
			if os.path.exists(picasafile):
				ret = import_picasa_faces(picasafile)
			if ret > 0:
				sys.stderr.write(self.style.SUCCESS(str(ret) + " new face(s) tagged.\n"))

		else:

			ret = import_photo_directory(full_path, tz)
			sys.stderr.write(self.style.SUCCESS(str(len(ret)) + " new photo(s) added.\n"))
			ret = bubble_photo_locations() + locate_photos_by_exif()
			if ret > 0:
				sys.stderr.write(self.style.SUCCESS(str(ret) + " photo(s) tagged with locations.\n"))
