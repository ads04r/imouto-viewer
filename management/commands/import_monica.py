from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import *
from viewer.importers import export_monica_thumbnails, import_monica_contact_mappings
from viewer.models import Person
import sys

class Command(BaseCommand):
	"""
	Command for importing/exporting life data to/from Monica (https://www.monicahq.com).
	"""
	def add_arguments(self, parser):

		choices = ['contacts', 'thumbnails', 'events']
		parser.add_argument('op', metavar='operation', type=str, nargs='+', choices=choices, help='Which operation to carry out.')

	def handle(self, *args, **kwargs):

		operations = kwargs['op']
		if 'contacts' in operations:
			for person in import_monica_contact_mappings():
				sys.stderr.write(self.style.SUCCESS("Linked " + str(person)))
		if 'thumbnails' in operations:
			for person in export_monica_thumbnails():
				sys.stderr.write(self.style.SUCCESS("Updated thumbnail for " + str(person)))
