from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import *
from viewer.importers import export_monica_thumbnails, import_monica_contact_mappings, export_monica_events, export_monica_calls
from viewer.models import Person, Event
import sys

class Command(BaseCommand):
	"""
	Command for importing/exporting life data to/from Monica (https://www.monicahq.com).
	"""
	def add_arguments(self, parser):

		choices = ['contacts', 'thumbnails', 'events', 'calls']
		parser.add_argument('op', metavar='operation', type=str, nargs='+', choices=choices, help='Which operation to carry out.')

	def handle(self, *args, **kwargs):

		operations = kwargs['op']
		if 'contacts' in operations:
			for person in import_monica_contact_mappings():
				sys.stderr.write(self.style.SUCCESS("Linked " + str(person)))
		if 'thumbnails' in operations:
			for person in export_monica_thumbnails():
				sys.stderr.write(self.style.SUCCESS("Updated thumbnail for " + str(person)))
		if 'events' in operations:
			for event in export_monica_events():
				sys.stderr.write(self.style.SUCCESS("Exported event on " + event.start_time.strftime("%Y-%m-%d") + ":" + str(event)))
		if 'calls' in operations:
			for call in export_monica_calls():
				sys.stderr.write(self.style.SUCCESS("Exported call on " + call.start_time.strftime("%Y-%m-%d") + ":" + str(call.address)))
