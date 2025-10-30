from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from viewer.importers.openscale import import_openscale
import os, sys

class Command(BaseCommand):
	"""
	Command for importing OpenScale export files.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="A file, exported from OpenScale.")
		parser.add_argument("-u", "--user", action="store", dest="user_id", required=True, help="which user are we working with?")

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])
		try:
			user = User.objects.get(username=kwargs['user_id'])
		except:
			user = None

		if not user:
			sys.stderr.write(self.style.ERROR(str(kwargs['user_id']) + " is not a valid user on this system.\n"))
			sys.exit(1)
		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)
		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			sys.exit(1)

		ret = {}
		for item in import_openscale(user, uploaded_file):
			type = item[1]
			if not(type in ret):
				ret[type] = 0
			ret[type] = ret[type] + 1
		for kk in ret.keys():
			k = str(kk)
			v = str(ret[k])
			sys.stderr.write(self.style.SUCCESS("Added " + str(v) + " " + k + " entries.\n"))




