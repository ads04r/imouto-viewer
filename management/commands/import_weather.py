from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import *
import os, sys, datetime, shutil, sqlite3, pytz, json, urllib.request

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

		api_key = settings.OPENWEATHERMAP_API_KEY

		for loc in kwargs['loc']:

			try:
				wloc = WeatherLocation.objects.get(id=loc)
			except:
				wloc = None

			if wloc is None:
				continue

			url = 'https://api.openweathermap.org/data/2.5/weather?id=' + wloc.api_id + '&appid=' + api_key
			with urllib.request.urlopen(url) as h:
				data = json.loads(h.read().decode())
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

# {'coord': {'lon': -1.4043, 'lat': 50.904}, 'weather': [{'id': 803, 'main': 'Clouds', 'description': 'broken clouds', 'icon': '04n'}], 
# 'base': 'stations', 'main': {'temp': 283.77, 'feels_like': 280.2, 'temp_min': 282.59, 'temp_max': 285.15, 'pressure': 1003, 'humidity': 87},
# 'visibility': 8000, 'wind': {'speed': 4.63, 'deg': 220}, 'clouds': {'all': 75}, 'dt': 1611855971, 'sys': {'type': 1, 'id': 1402, 'country': 'GB', 'sunrise': 1611820054, 'sunset': 1611852563}, 'timezone': 0, 'id': 2637487, 'name': 'Southampton', 'cod': 200}
# dict_keys(['coord', 'weather', 'base', 'main', 'visibility', 'wind', 'clouds', 'dt', 'sys', 'timezone', 'id', 'name', 'cod'])

#    time = models.DateTimeField()
#    location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, related_name='readings')
#    description = models.CharField(max_length=128, blank=True, null=True)
#    temperature = models.FloatField(blank=True, null=True)
#    wind_speed = models.FloatField(blank=True, null=True)
#    wind_direction = models.IntegerField(blank=True, null=True)
#    humidity = models.IntegerField(blank=True, null=True)
#    visibility = models.IntegerField(blank=True, null=True)

