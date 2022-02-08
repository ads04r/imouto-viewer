from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_home_assistant_presence
from viewer.models import PersonProperty
import sys

class Command(BaseCommand):
	"""
	Command for importing presence information from Home Assistant. Requires HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN to be set.
	"""
	def handle(self, *args, **kwargs):

		for prop in PersonProperty.objects.filter(key='hassentity').values('person__uid', 'value').distinct():
			ret = import_home_assistant_presence(prop['person__uid'], prop['value'])
			sys.stderr.write(self.style.SUCCESS(str(len(ret)) + " event(s) tagged with entity " + prop['value'] + ".\n"))
