from django.core.management.base import BaseCommand
from viewer.importers.pidgin import import_pidgin_log_file
import os, sys

#>>> from viewer.importers.pidgin import import_pidgin_log_file

#        :param uid: The Imouto uid of the other person in the conversation.
#        :param name: The name of the other person in the conversation, as it appears in the log file.


class Command(BaseCommand):
	"""
	Command for importing IM messages from a Pidgin log file in plain text format. Currently only works reliably with direct message chat logs, with only two participants.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", required=True, help="The Pidgin log file to be imported.")
		parser.add_argument("-u", "--user", action="store", dest="input_uid", required=True, help="The Imouto uid of the other person in the conversation.")
		parser.add_argument("-n", "--name", action="store", dest="input_name", required=True, help="The name of the other person in the conversation, as it appears in the log file (which may be different to their actual name)")

	def handle(self, *args, **kwargs):

		path = os.path.abspath(kwargs['input_file'])
		user = kwargs['input_uid']
		name = kwargs['input_name']

		if not(os.path.exists(path)):
			sys.stderr.write(self.style.ERROR("Log file not found.\n"))
			sys.exit(1)

		ct = import_pidgin_log_file(path, user, name)
		if ct == 0:
			sys.stderr.write(self.style.WARNING("No new messages imported.\n"))
		else:
			sys.stderr.write(self.style.SUCCESS("Successfully imported " + str(ct) + " message(s).\n"))
