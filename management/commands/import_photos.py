from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_photo_directory
from viewer.functions import bubble_photo_locations, locate_photos_by_exif
import os, sys, pytz

class Command(BaseCommand):
	"""
	Command for importing photos and related information, such as GPS positions and face information.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="photo_path", default="", help="A path to search for photos.")
		parser.add_argument("-z", "--timezone", action="store", dest="tz_info", default="", help="The timezone of the photos, useful for when none is specified in the EXIF data.")

	def handle(self, *args, **kwargs):

		path = kwargs['photo_path']
		tz_string = kwargs['tz_info']
		if tz_string == '':
			if settings.TIME_ZONE:
				tz = pytz.timezone(settings.TIME_ZONE)
			else:
				tz = pytz.UTC
		else:
			tz = pytz.timezone(tz_string)
		if len(path) == 0:
			sys.stderr.write(self.style.ERROR("Invalid path to images; must be specified using the --input argument.\n"))
			sys.exit(1)
		if not(os.path.isdir(path)):
			sys.stderr.write(self.style.ERROR("Path '" + path + "' not found.\n"))
			sys.exit(1)

		ret = import_photo_directory(path, tz)
		sys.stderr.write(self.style.SUCCESS(str(len(ret)) + " new photo(s) added.\n"))
		ret = bubble_photo_locations() + locate_photos_by_exif()
		sys.stderr.write(self.style.SUCCESS(str(ret) + " photo(s) tagged with locations.\n"))
