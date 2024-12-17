from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers.trackandgraph import import_trackandgraph
import os, sys

class Command(BaseCommand):
	"""
	Command for importing statistics from a Track and Graph backup file.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="A file exported from the Android app Track and Graph using the backup function.")

	def handle(self, *args, **kwargs):

		path = os.path.abspath(kwargs['input_file'])
		if not os.path.exists(path):
			sys.stderr.write("File " + path + " not found.\n")
			sys.exit(1)

		import_trackandgraph(path)
