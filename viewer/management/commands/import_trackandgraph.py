from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from viewer.importers.trackandgraph import import_trackandgraph
import os, sys

class Command(BaseCommand):
	"""
	Command for importing statistics from a Track and Graph backup file.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-u", "--user", action="store", dest="user_id", required=True, help="which user are we working with?")
		parser.add_argument("-i", "--input", action="store", dest="input_file", required=True, help="A file exported from the Android app Track and Graph using the backup function.")

	def handle(self, *args, **kwargs):

		try:
			user = User.objects.get(username=kwargs['user_id'])
		except:
			user = None
		if not user:
			sys.stderr.write(self.style.ERROR(str(kwargs['user_id']) + " is not a valid user on this system.\n"))
			sys.exit(1)
		path = os.path.abspath(kwargs['input_file'])
		if not os.path.exists(path):
			sys.stderr.write(self.style.ERROR("File " + path + " not found.\n"))
			sys.exit(1)

		import_trackandgraph(user, path)
