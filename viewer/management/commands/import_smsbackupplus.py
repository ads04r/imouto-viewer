from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from dateutil.parser import parse as dateparse
from viewer.models import Person, PersonProperty
from django.db.models import Q
from django.core.files import File
from xml.dom import minidom
from requests import request
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from PIL import Image
import sys, vobject
from viewer.importers.messages import import_sms_from_imap, import_calls_from_imap

class Command(BaseCommand):
	"""
	Command for importing SMS messages from IMAP, as put there by the Android app SMSBackup+
	"""
	def add_arguments(self, parser):

		parser.add_argument("host", action="store", help="The hostname or IP address of the IMAP server.")
		parser.add_argument("-u", "--username", action="store", dest="username", default="", help="User name for logging into the IMAP server.")
		parser.add_argument("-p", "--password", action="store", dest="password", default="", help="Password for logging into the IMAP server.")
		parser.add_argument("-i", "--inbox", action="store", dest="inbox", default="INBOX", help="The name of the inbox in which the SMS messages may be found.")
		parser.add_argument("-o", "--operation", action="store", dest="operation", default="sms", choices=['sms', 'phone'], help="The mode of operation. 'sms' imports text messages, 'phone' imports phone calls.")

	def handle(self, *args, **kwargs):

		host = kwargs['host']
		username = kwargs['username']
		password = kwargs['password']
		mode = kwargs['operation']
		inbox = kwargs['inbox']
		if ((username == '') or (password == '')):
			sys.stderr.write(self.style.ERROR("Must supply username and password details.\n"))
			sys.exit(1)

		if mode == 'phone':
			ct = import_calls_from_imap(host, username, password, inbox)
		elif mode == 'sms':
			ct = import_sms_from_imap(host, username, password, inbox)
		else:
			sys.stderr.write(self.style.ERROR("Invalid operation mode.\n"))
			sys.exit(1)

		if ct == -1:
			sys.stderr.write(self.style.ERROR("Error logging into server.\n"))
			sys.exit(1)

		if ct == 0:
			if mode == 'phone':
				sys.stderr.write(self.style.SUCCESS("No new call logs on server.\n"))
			if mode == 'sms':
				sys.stderr.write(self.style.SUCCESS("No new messages on server.\n"))
			return

		if mode == 'phone':
			sys.stderr.write(self.style.SUCCESS("Successfully imported " + str(ct) + " call log(s).\n"))
		if mode == 'sms':
			sys.stderr.write(self.style.SUCCESS("Successfully imported " + str(ct) + " message(s).\n"))
