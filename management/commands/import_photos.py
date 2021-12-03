from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_photo_directory
import os, sys, pytz

class Command(BaseCommand):
	"""
	Command for importing photos and related information, such as GPS positions and face information.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="photo_path", default="", help="A path to search for photos.")

	def handle(self, *args, **kwargs):

		path = kwargs['photo_path']
		if len(path) == 0:
			sys.stderr.write(self.style.ERROR("Invalid path to images; must be specified using the --input argument.\n"))
			sys.exit(1)
		if not(os.path.isdir(path)):
			sys.stderr.write(self.style.ERROR("Path '" + path + "' not found.\n"))
			sys.exit(1)

		ret = import_photo_directory(path, pytz.timezone(settings.TIME_ZONE))
		sys.stderr.write(self.style.SUCCESS(str(len(ret)) + " new photo(s) found.\n"))
