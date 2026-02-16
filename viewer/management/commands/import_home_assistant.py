from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.contrib.auth.models import User
from viewer.importers.home_assistant import import_home_assistant_presence, import_home_assistant_readings, import_home_assistant_events
from viewer.models import PersonProperty
import sys

class Command(BaseCommand):
	"""
	Command for importing presence information from Home Assistant. Requires HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN to be set.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-u", "--user", action="store", dest="user_id", required=True, help="which user are we working with?")

	def handle(self, *args, **kwargs):

		try:
			user = User.objects.get(username=kwargs['user_id'])
		except:
			user = None
		if not user:
			sys.stderr.write(self.style.ERROR(str(kwargs['user_id']) + " is not a valid user on this system.\n"))
			sys.exit(1)

		try:
			logging = user.profile.settings['HOME_ASSISTANT_LOGGING']
		except KeyError:
			logging = []

		try:
			events = user.profile.settings['HOME_ASSISTANT_EVENTS']
		except KeyError:
			events = []

		for prop in PersonProperty.objects.filter(key='hassentity').values('person__uid', 'value').distinct():
			ret = import_home_assistant_presence(user, prop['person__uid'], prop['value'])
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " event(s) tagged with entity " + prop['value'] + ".\n"))

		for item in logging:
			if len(item) > 2:
				ret = import_home_assistant_readings(user, item[0], item[1], days=7, multiplier=item[2])
			else:
				ret = import_home_assistant_readings(user, item[0], item[1], days=7)
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " data readings of type " + item[1] + " added.\n"))

		for item in events:
			ret = import_home_assistant_events(user, item[0], item[1], item[2], days=2)
			ct = len(ret)
			if ct > 0:
				sys.stderr.write(self.style.SUCCESS(str(ct) + " data readings of type " + item[1] + " added.\n"))
