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
from viewer.importers.dav import import_carddav

class Command(BaseCommand):
	"""
	Command for importing people from a CardDAV URL.
	"""
	def add_arguments(self, parser):

		parser.add_argument("url", action="store", help="The URL of the CardDAV instance.")
		parser.add_argument("-u", "--username", action="store", dest="username", default="", help="User name for logging into CardDAV instance.")
		parser.add_argument("-p", "--password", action="store", dest="password", default="", help="Password for logging into CardDAV instance.")
		parser.add_argument("-a", "--auth", action="store", dest="authtype", default="digest", choices=['none', 'basic', 'digest'], help="Authentication type supported by the CardDAV instance. May be basic or digest.")

	def handle(self, *args, **kwargs):

		url = kwargs['url']
		username = kwargs['username']
		password = kwargs['password']
		authtype = kwargs['authtype']
		if ((username == '') or (password == '')):
			username = ''
			password = ''
			authtype = 'none'

		auth = None
		if authtype == 'basic':
			auth = HTTPBasicAuth(username, password)
		if authtype == 'digest':
			auth = HTTPDigestAuth(username, password)

		import_carddav(url, auth)

