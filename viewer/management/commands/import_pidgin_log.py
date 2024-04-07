from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import RemoteInteraction
from viewer.importers.im import import_pidgin_log
import os, sys

class Command(BaseCommand):
	"""
	Command for importing IM messages from a Pidgin log file in plain text format.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="The file, containing SMS messages, to be imported.")
		parser.add_argument("-t", "--type", action="store", dest="input_type", default="", help="The type of IM being used (ie msn, slack, icq, telegram, ...)")
		parser.add_argument("-u", "--user", action="store", dest="input_handle", default="", help="The handle of the Imouto user in this log file, to ensure outgoing and incoming messages are labelled accordingly.")
		parser.add_argument("-c", "--contact", action="store", dest="input_contact", default="", help="Optional, allows the override of the chat recipient's name with an imouto person uid.")

	def handle(self, *args, **kwargs):

		path = os.path.abspath(kwargs['input_file'])
		type = ("im_" + kwargs['input_type']).strip('_')
		user = kwargs['input_handle']
		contact = kwargs['input_contact']

		if not(os.path.exists(path)):
			sys.exit()

		if len(user) == 0:
			sys.exit()
		if len(type) == 0:
			sys.exit()

		ret = import_pidgin_log(path, type, user, contact)

		print(ret)
