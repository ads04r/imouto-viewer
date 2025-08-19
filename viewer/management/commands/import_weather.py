from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import *
import os, sys, datetime, shutil, sqlite3, pytz, json, requests

class Command(BaseCommand):
	"""
	Command for importing weather data from OpenWeatherMap. This functionality needs the OPENWEATHERMAP_API_KEY setting to be set.
	"""
	def add_arguments(self, parser):

		choices = []
		for loc in WeatherLocation.objects.all():
			choices.append(loc.id)
		parser.add_argument('loc', metavar='location', type=str, nargs='+', choices=choices, help='The location ID of the place whose weather we are to import.')

	def handle(self, *args, **kwargs):

		try:
			api_key = settings.OPENWEATHERMAP_API_KEY
		except:
			sys.stderr.write(self.style.ERROR("Settings OPENWEATHERMAP_API_KEY is not set.\n"))
			sys.exit(1)

		for loc in kwargs['loc']:

			try:
				wloc = WeatherLocation.objects.get(id=loc)
			except:
				wloc = None

			if wloc is None:
				continue

			url = 'https://api.openweathermap.org/data/2.5/weather?id=' + wloc.api_id + '&appid=' + api_key
			with requests.get(url) as r:
				data = json.loads(r.text)
			wloc.lat = data['coord']['lat']
			wloc.lon = data['coord']['lon']
			wloc.label = data['name']
			wloc.save()

			dt = datetime.datetime.fromtimestamp(data['dt'], tz=pytz.UTC)
			temp = float(data['main']['temp']) - 273.15 # default temperature is in Kelvin
			temp = float(int(temp * 100)) / 100 # 2dp
			description = 'Unknown'
			items = []
			for item in data['weather']:
				items.append(item['description'])
			if len(items) > 0:
				description = ', '.join(items)
			reading = WeatherReading(time=dt, location=wloc, description=description, temperature=temp, wind_speed=data['wind']['speed'], wind_direction=data['wind']['deg'], humidity=data['main']['humidity'], visibility=data['visibility'])
			reading.save()
