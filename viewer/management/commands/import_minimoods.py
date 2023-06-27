from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_data
from dateutil import parser
import os, sys, csv, datetime

class Command(BaseCommand):
	"""
	Command for importing a Minimoods export file. This file should be a CSV file, generated using the export function in Minimoods for Android.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="A pebble data file, copied from the data directory of the Pebble Android app.")

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])

		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)

		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			sys.exit(1)

		data = []
		with open(uploaded_file, newline='\n') as csvfile:
			r = csv.reader(csvfile, delimiter=',', quotechar='"')
			for row in r:
				if len(row) < 2:
					continue
				dts = parser.parse(row[0])
				dte = dts + datetime.timedelta(seconds=86400)
				v = 6 - int(row[1])
				if v > 5:
					continue
				if v < 1:
					continue
				data.append({'start_time': dts, 'end_time': dte, 'type': 'mood', 'value': v})

		if len(data) == 0:
			sys.stderr.write(self.style.ERROR("Cannot import - the file contains no readable data."))
			sys.exit(1)
		c = import_data(data)
		if c == 0:
			sys.stderr.write(self.style.ERROR("Cannot import - either there is no data, or all the data in the file already exists."))
			sys.exit(1)
		print(c)
