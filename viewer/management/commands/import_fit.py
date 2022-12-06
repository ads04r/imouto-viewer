from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import DataReading, Event
from io import StringIO
import os, sys, datetime, shutil, sqlite3, pytz, csv, xmltodict, json
from viewer.models import RemoteInteraction
from viewer.importers import import_fit

class Command(BaseCommand):
	"""
	Command for importing health data from an ANT-FIT (Garmin) file
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="The file, containing SMS messages, to be imported.")

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])

		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)

		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			sys.exit(1)

		sys.stderr.write(self.style.SUCCESS(uploaded_file + '\n'))
		import_fit(uploaded_file)
