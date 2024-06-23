from django.db.models import Count, Sum, Max, Min
from django.conf import settings
from viewer.models import Event
from bs4 import BeautifulSoup
import datetime, pytz, json, requests

from viewer.models import Year, YearChart, YearProperty, YearGraph
from viewer.models import DataReading, RemoteInteraction
from viewer.models import Location, Person, Photo
from viewer.functions.moonshine import get_moonshine_artist_image

import logging
logger = logging.getLogger(__name__)

def generate_year_travel(year):

	countries = year.countries.count()
	if countries > 1:
		prop = year.add_property(key='Countries Visited', value=(countries - 1), category='travel', icon='globe')

def generate_year_health(year):

	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1) # the second subtraction supports leap-seconds, assuming Django does
	steps = DataReading.objects.filter(type='step-count', start_time__gte=dts, end_time__lte=dte).aggregate(steps=Sum('value'))['steps']
	ww = DataReading.objects.filter(type='weight', start_time__gte=dts, end_time__lte=dte).aggregate(max=Max('value'), min=Min('value'))
	max_weight = None
	min_weight = None
	if ww['max']:
		max_weight = float(ww['max']) / 1000.0
	if ww['min']:
		min_weight = float(ww['min']) / 1000.0
	days = ((dte - dts).total_seconds() + 1.0) / 86400.0
	steps_per_day = None
	if steps:
		steps_per_day = int(float(steps) / days)

	for workout in year.workouts():
		prop = year.add_property(key=workout[0] + ' distance', value=workout[1], category='health', icon=workout[2])
		prop.description='miles'
		prop.save(update_fields=['description'])
	if steps:
		prop = year.add_property(key='Total steps', value=steps, category='health', icon='male')
	if steps_per_day:
		prop = year.add_property(key='Steps per day', value=steps_per_day, category='health', icon='male')
		prop.description='mean'
		prop.save(update_fields=['description'])
	if max_weight:
		prop = year.add_property(key='Highest weight', value=max_weight, category='health', icon='balance-scale')
		prop.description='kg'
		prop.save(update_fields=['description'])
	if min_weight:
		prop = year.add_property(key='Lowest weight', value=min_weight, category='health', icon='balance-scale')
		prop.description='kg'
		prop.save(update_fields=['description'])

def generate_year_photos(year):

	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)

	photos = Photo.objects.filter(time__gte=dts, time__lte=dte).count()
	photos_gps = Photo.objects.filter(time__gte=dts, time__lte=dte).exclude(lat=None).exclude(lon=None).count()
	photos_location = Photo.objects.filter(time__gte=dts, time__lte=dte).exclude(location=None).count()
	photos_of_people = Photo.objects.filter(time__gte=dts, time__lte=dte).annotate(Count('people')).exclude(people__count=0)
	photos_people = photos_of_people.count()
	photos_location_chart = Location.objects.filter(photos__time__gte=dts, photos__time__lte=dte).annotate(photo_count=Count('photos')).order_by('-photo_count')
	photos_person_chart = Person.objects.filter(photo__time__gte=dts, photo__time__lte=dte).annotate(photo_count=Count('photo')).order_by('-photo_count')

	prop = year.add_property(key='Photos Taken', value=photos, category='photos', icon='camera')
	prop = year.add_property(key='Photos with GPS', value=photos_gps, category='photos', icon='map-marker')
	prop = year.add_property(key='Photos with Location', value=photos_location, category='photos', icon='map')

	if (photos + photos_location) > 1:
		year.add_graph(text='Photos with Known Locations', type='donut', description='', category='photos', graph_data=[["Known", "Unknown"],[photos_location, (photos - photos_location)]])

	prop = year.add_property(key='Photos of People', value=photos_people, category='photos', icon='user')

	chart_data = []
	for loc in photos_location_chart:
		item = {'text': str(loc), 'value': loc.photo_count}
		chart_data.append(item)
	if len(chart_data) > 10:
		chart_data = chart_data[0:10]
	if len(chart_data) > 0:
		year.add_chart(text='Most Photographed Places', category='photos', chart_data=chart_data)

	chart_data = []
	for person in photos_person_chart:
		item = {'text': str(person), 'value': person.photo_count}
		if person.image:
			item['image'] = person.image.path
		chart_data.append(item)
	if len(chart_data) > 10:
		chart_data = chart_data[0:10]
	if len(chart_data) > 0:
		year.add_chart(text='Most Photographed People', category='photos', chart_data=chart_data)

def generate_year_comms(year):

	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)

	phone_calls_made = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=False).count()
	phone_calls_recv = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=True).exclude(message__icontains='(missed call)').count()
	phone_calls_miss = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=True, message__icontains='(missed call)').count()
	if (phone_calls_made + phone_calls_recv) > 1:
		prop = year.add_property(key='Phone Calls', value=(phone_calls_made + phone_calls_recv), category='communication', icon='phone')
		prop.description = str(phone_calls_made) + ' made / ' + str(phone_calls_recv) + ' received'
		prop.save()
		year.add_graph(text='Calls Received vs Calls Made', type='donut', description='', icon='', category='communication', graph_data=[["Made", "Received"],[phone_calls_made, phone_calls_recv]])
		year.add_graph(text='Calls Taken vs Calls Missed', type='donut', description='', icon='', category='communication', graph_data=[["Answered", "Missed"],[phone_calls_recv, phone_calls_miss]])

	sms_sent = RemoteInteraction.objects.filter(type='sms', time__gte=dts, time__lte=dte, incoming=False).count()
	sms_recv = RemoteInteraction.objects.filter(type='sms', time__gte=dts, time__lte=dte, incoming=True).count()
	if (sms_sent + sms_recv) > 1:
		prop = year.add_property(key='SMS', value=(sms_sent + sms_recv), category='communication', icon='comment-o')
		prop.description = str(sms_sent) + ' sent / ' + str(sms_recv) + ' received'
		prop.save()
		year.add_graph(text='SMS Sent vs SMS Received', type='donut', description='', icon='', category='communication', graph_data=[["Sent", "Received"],[sms_sent, sms_recv]])

def generate_year_music(year, moonshine_url=''):

	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 1, 1, 0, 0, 0))

	if len(moonshine_url) > 0:
		report_url = moonshine_url.rstrip('/') + '/report/' + str(dts.year)
		music_data = {}
		try:
			req = requests.get(report_url)
			if(req.status_code == 200):
				music_data = json.loads(req.text)
		except:
			music_data = {}
		if len(music_data) > 0:
			if 'charts' in music_data:
				if 'artists' in music_data['charts']:
					chart_data = []
					for artist in music_data['charts']['artists']:
						item = {'text': artist['name'], 'value': artist['plays']}
						image = get_moonshine_artist_image(artist['mbid'])
						if image:
							item['image'] = image
						chart_data.append(item)
					if len(chart_data) > 0:
						year.add_chart(text='Most Played Artists', category='music', chart_data=chart_data)
				if 'tracks' in music_data['charts']:
					chart_data = []
					for track in music_data['charts']['tracks']:
						mbid = track['mbid']
						item = {'text': track['title'], 'value': track['plays']}
						image = None
						track_url = moonshine_url.rstrip('/') + '/track/' + str(mbid)
						req = requests.get(track_url)
						if(req.status_code == 200):
							track_data = json.loads(req.text)
							artist_data = {}
							if 'artists' in track_data:
								if isinstance(track_data['artists'], list):
									if len(track_data['artists']) > 0:
										artist_data = track_data['artists'][0]
							if 'name' in artist_data:
								item['text'] = artist_data['name'] + ' - ' + track['title']
							if 'mbid' in artist_data:
								image = get_moonshine_artist_image(artist_data['mbid'])
						if image:
							item['image'] = image
						chart_data.append(item)
					if len(chart_data) > 0:
						year.add_chart(text='Most Played Songs', category='music', chart_data=chart_data)
			if 'play_count' in music_data:
				prop = year.add_property(key='Tracks played', icon='music', value=str(music_data['play_count']), category='music')
				if 'track_count' in music_data:
					prop.description = str(music_data['track_count']) + ' unique tracks'
					prop.save(update_fields=['description'])
			if 'artist_count' in music_data:
				prop = year.add_property(key='Artists played', value=str(music_data['artist_count']), category='music', icon='users')
				if 'discovery' in music_data:
					if 'artists' in music_data['discovery']:
						prop.description = str(len(music_data['discovery']['artists'])) + ' new artists discovered'
						prop.save(update_fields=['description'])
			if 'album_count' in music_data:
				prop = year.add_property(key='Albums played', value=str(music_data['album_count']), category='music', icon='play-circle')
				if 'discovery' in music_data:
					if 'albums' in music_data['discovery']:
						prop.description = str(len(music_data['discovery']['albums'])) + ' albums discovered'
						prop.save(update_fields=['description'])

def generate_year_movies(year, username=''):

	if len(username) > 0:

		title = "Movies Seen in " + str(year.year)

		for chart in YearChart.objects.filter(year=year, text=title):
			chart.delete()

		url = "https://letterboxd.com/" + str(username) + "/films/diary/for/" + str(year.year) + "/"
		session = requests.Session()
		session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win94; x64; rv:55.0) Gecko/20100101 Firefox/55.0"})
		r = session.get(url, allow_redirects=True, timeout=10)
		html = r.text

		soup = BeautifulSoup(html, features='html.parser')
		chart_data = []
		for link in soup.findAll('a'):

			try:
				ds = link['data-viewing-date']
			except:
				ds = ''
			if ds == '':
				continue

			label = link['data-film-name']
			dt = datetime.datetime.strptime(ds, '%Y-%m-%d').date().strftime("%-d %B")
			item = {'text': label, 'value': dt}
			chart_data.append(item)

		if len(chart_data) > 2:
			chart_data.reverse()
			year.add_chart(text=title, category='movies', chart_data=chart_data)

