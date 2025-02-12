from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from dateutil.parser import parse as dateparse
from viewer.importers.dav import import_calendar_feed
from tqdm import tqdm
import os, sys, datetime, pytz, requests

class Command(BaseCommand):
	"""
	Command for importing calendars. This functionality needs the ICAL_URLS setting to be set.
	"""
	def handle(self, *args, **kwargs):

		try:
			urls = settings.ICAL_URLS
		except:
			urls = None
		if not(isinstance(urls, (list))):
			sys.stderr.write(self.style.ERROR("ICAL_URLS setting must be a list of ICS URLs.\n"))
			sys.exit(1)

		for calendar_data in tqdm(urls, bar_format='{l_bar}{bar} | {n_fmt}/{total_fmt} ({remaining} remaining)', colour='#00af00'):

			username = None
			password = None
			if isinstance(calendar_data, str):
				url = calendar_data
			else:
				url = calendar_data[0]
				username = calendar_data[1]
				password = calendar_data[2]

			ret = import_calendar_feed(url, username, password)
