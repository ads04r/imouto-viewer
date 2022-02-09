from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.importers import import_home_assistant_presence, import_home_assistant_readings, import_home_assistant_events
from viewer.models import PersonProperty
import sys

class Command(BaseCommand):
	"""
	Command for importing presence information from Home Assistant. Requires HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN to be set.
	"""
	def handle(self, *args, **kwargs):

		try:
			logging = settings.HOME_ASSISTANT_LOGGING
		except AttributeError:
			logging = []

		try:
			events = settings.HOME_ASSISTANT_EVENTS
		except AttributeError:
			events = []

		for prop in PersonProperty.objects.filter(key='hassentity').values('person__uid', 'value').distinct():
			ret = import_home_assistant_presence(prop['person__uid'], prop['value'])
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " event(s) tagged with entity " + prop['value'] + ".\n"))

		for item in logging:
			ret = import_home_assistant_readings(item[0], item[1], days=7)
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " data readings of type " + item[1] + " added.\n"))

		for item in events:
			ret = import_home_assistant_events(item[0], item[1], days=2)
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " events of type " + item[1] + " added.\n"))
