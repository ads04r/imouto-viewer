from django.core.management.base import BaseCommand
from django.conf import settings
import datetime, requests

from viewer.models import HistoricalEvent

class Command(BaseCommand):
	"""
	Command for importing HistoricalEvents from Wikipedia
	"""
	def add_arguments(self, parser):

		parser.add_argument("-d", "--date", action="store", dest="date", default="", help="The date to import.")
		parser.add_argument("-y", "--year", action="store", dest="year", default="", help="The year from which to begin importing events.")

	def handle(self, *args, **kwargs):

		ds = kwargs['date']
		dt = datetime.datetime.now().date()
		if '-' in ds:
			dsa = ds.split('-')
			dsd = int(dsa[-1])
			dsm = int(dsa[-2])
			if((dsd >= 1) & (dsd <= 31) & (dsm >= 1) & (dsm <= 12)):
				dt = datetime.date(dt.year, dsm, dsd)

		url = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/selected/" + dt.strftime("%m/%d")
		with requests.get(url, headers={'User-Agent': settings.USER_AGENT}, allow_redirects=True) as r:
			data = r.json()
		if not 'selected' in data:
			return
		last_year = 0
		if len(kwargs['year']) >= 4:
			last_year = int(kwargs['year'])
		HistoricalEvent.objects.filter(date__month=dt.month, date__day=dt.day, category='world_events').delete()
		for item in data['selected']:
			if not 'year' in item:
				continue
			if last_year > item['year']:
				continue
			dd = datetime.date(item['year'], dt.month, dt.day)
			event = HistoricalEvent(date=dd, category='world_events', description=item['text'])
			event.save()
