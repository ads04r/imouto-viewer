from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
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
				dt = dt.replace(day=dsd, month=dsm)
		ds = dt.strftime("%B") + ' ' + (dt.strftime("%d").lstrip('0'))
		url = "https://en.wikipedia.org/wiki/" + ds.replace(' ', '_')
		r = requests.get(url)
		soup = BeautifulSoup(r.content, features='lxml')
		last_year = 1900
		events = []
		if len(kwargs['year']) >= 4:
			last_year = int(kwargs['year'])
		div = soup.find('div', class_='mw-body-content')
		for ul in div.find_all('ul'):
			for li in ul.find_all('li'):
				text = li.text
				if '(d. ' in text:
					break
				if '(b. ' in text:
					break
				if not('–' in text):
					continue
				parsed = text.split('–')
				if len(parsed) != 2:
					continue
				if ':' in parsed[1]:
					continue
				try:
					y = int(parsed[0].strip())
				except:
					y = -1
				if y < last_year:
					continue
				last_year = y
				event_date = dt.replace(year=y)
				parsed = parsed[1].split('[')
				text = parsed[0].strip()
				events.append([event_date, text])

		if len(events) > 0:

			HistoricalEvent.objects.filter(date__month=dt.month, date__day=dt.day, category='world_events').delete()
			for event in events:
				item = HistoricalEvent(date=event[0], category='world_events', description=event[1])
				item.save()
