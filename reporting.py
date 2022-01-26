from django.db.models import Count
from .models import LifeReport, Event
from .functions import *
from tzlocal import get_localzone
import datetime, pytz, os, random

def generate_report_travel(report, dts, dte):

	countries = report.countries().count()
	if countries > 1:
		prop = report.addproperty(key='Countries Visited', value=(countries - 1), category='travel')
		prop.icon = 'globe'
		prop.save()

def generate_report_photos(report, dts, dte):

	options = json.loads(report.options)

	photos = Photo.objects.filter(time__gte=dts, time__lte=dte).count()
	photos_gps = Photo.objects.filter(time__gte=dts, time__lte=dte).exclude(lat=None).exclude(lon=None).count()
	photos_location = Photo.objects.filter(time__gte=dts, time__lte=dte).exclude(location=None).count()
	photos_of_people = Photo.objects.filter(time__gte=dts, time__lte=dte).annotate(Count('people')).exclude(people__count=0)
	photos_people = photos_of_people.count()
	photos_location_chart = Location.objects.filter(photos__time__gte=dts, photos__time__lte=dte).annotate(photo_count=Count('photos')).order_by('-photo_count')
	photos_person_chart = Person.objects.filter(photo__time__gte=dts, photo__time__lte=dte).annotate(photo_count=Count('photo')).order_by('-photo_count')

	prop = report.addproperty(key='Photos Taken', value=photos, category='photos')
	prop.icon = 'camera'
	prop.save()

	prop = report.addproperty(key='Photos with GPS', value=photos_gps, category='photos')
	prop.icon = 'map-marker'
	prop.save()

	prop = report.addproperty(key='Photos with Location', value=photos_location, category='photos')
	prop.icon = 'map'
	prop.save()

	if (photos + photos_location) > 1:
		callg1 = LifeReportGraph(key='Photos with Known Locations', type='donut', description='', icon='', report=report, category='photos', data=json.dumps([["Known", "Unknown"],[photos_location, (photos - photos_location)]]))
		callg1.save()

	prop = report.addproperty(key='Photos of People', value=photos_people, category='photos')
	prop.icon = 'user'
	prop.save()

	chart_data = []
	for loc in photos_location_chart:
		item = {'text': str(loc), 'value': loc.photo_count}
		chart_data.append(item)
	if len(chart_data) > 10:
		chart_data = chart_data[0:10]
	if len(chart_data) > 0:
		chart = LifeReportChart(text='Most Photographed Locations', data=json.dumps(chart_data), report=report)
		chart.save()

	if options['peoplestats']:
		chart_data = []
		for person in photos_person_chart:
			item = {'text': str(person), 'value': person.photo_count}
			if person.image:
				item['image'] = person.image.path
			chart_data.append(item)
		if len(chart_data) > 10:
			chart_data = chart_data[0:10]
		if len(chart_data) > 0:
			chart = LifeReportChart(text='Most Photographed People', data=json.dumps(chart_data), report=report)
			chart.save()

def generate_report_people(report, dts, dte):

	ReportPeople.objects.filter(report=report).delete()

	for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte).exclude(type='life_event'):
		for person in event.people.all():
			try:
				rp = ReportPeople.objects.get(report=report, person=person)
			except:
				rp = ReportPeople(report=report, person=person, first_encounter=event.start_time, day_list='[]')
				rp.save()
			day_list = json.loads(rp.day_list)
			ds = event.start_time.strftime('%Y-%m-%d')
			changed = False
			if not(ds in day_list):
				day_list.append(ds)
				rp.day_list = json.dumps(day_list)
				changed = True
			if event.start_time < rp.first_encounter:
				rp.first_encounter = event.start_time
				changed = True
			if changed:
				rp.save()

	tz = get_localzone()
	now = pytz.UTC.localize(datetime.datetime.utcnow())
	report.modified_date=now
	report.save()

def generate_report_comms(report, dts, dte):

	phone_calls_made = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=False).count()
	phone_calls_recv = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=True).exclude(message__icontains='(missed call)').count()
	phone_calls_miss = RemoteInteraction.objects.filter(type='phone-call', time__gte=dts, time__lte=dte, incoming=True, message__icontains='(missed call)').count()
	if (phone_calls_made + phone_calls_recv) > 1:
		prop = report.addproperty(key='Phone Calls', value=(phone_calls_made + phone_calls_recv), category='communication')
		prop.icon = 'phone'
		prop.description = str(phone_calls_made) + ' made / ' + str(phone_calls_recv) + ' received'
		prop.save()
		callg1 = LifeReportGraph(key='Calls Received vs Calls Made', type='donut', description='', icon='', report=report, category='communication', data=json.dumps([["Made", "Received"],[phone_calls_made, phone_calls_recv]]))
		callg1.save()
		callg2 = LifeReportGraph(key='Calls Taken vs Calls Missed', type='donut', description='', icon='', report=report, category='communication', data=json.dumps([["Answered", "Missed"],[phone_calls_recv, phone_calls_miss]]))
		callg2.save()

	sms_sent = RemoteInteraction.objects.filter(type='sms', time__gte=dts, time__lte=dte, incoming=False).count()
	sms_recv = RemoteInteraction.objects.filter(type='sms', time__gte=dts, time__lte=dte, incoming=True).count()
	if (sms_sent + sms_recv) > 1:
		prop = report.addproperty(key='SMS', value=(sms_sent + sms_recv), category='communication')
		prop.icon = 'comment-o'
		prop.description = str(sms_sent) + ' sent / ' + str(sms_recv) + ' received'
		prop.save()
		smsg1 = LifeReportGraph(key='SMS Sent vs SMS Received', type='donut', description='', icon='', report=report, category='communication', data=json.dumps([["Sent", "Received"],[sms_sent, sms_recv]]))
		smsg1.save()

def generate_report_music(report, dts, dte, moonshine_url=''):

	if len(moonshine_url) > 0:
		report_url = moonshine_url.rstrip('/') + '/report/' + str(dts.year)
		music_data = {}
		try:
			req = urllib.request.urlopen(report_url)
			if(req.getcode() == 200):
				music_data = json.loads(req.read())
		except:
			music_data = {}
		if len(music_data) > 0:
			if 'charts' in music_data:
				if 'artists' in music_data['charts']:
					chart_data = []
					for artist in music_data['charts']['artists']:
						item = {'text': artist['name'], 'value': artist['plays']}
						chart_data.append(item)
					if len(chart_data) > 0:
						chart = LifeReportChart(text='Most Played Artists', data=json.dumps(chart_data), report=report)
						chart.save()
			if 'play_count' in music_data:
				prop = report.addproperty(key='Tracks played', value=str(music_data['play_count']), category='music')
				prop.icon = 'music'
				if 'track_count' in music_data:
					prop.description = str(music_data['track_count']) + ' unique tracks'
				prop.save()
			if 'artist_count' in music_data:
				prop = report.addproperty(key='Artists played', value=str(music_data['artist_count']), category='music')
				prop.icon = 'users'
				if 'discovery' in music_data:
					if 'artists' in music_data['discovery']:
						prop.description = str(len(music_data['discovery']['artists'])) + ' new artists discovered'
				prop.save()
			if 'album_count' in music_data:
				prop = report.addproperty(key='Albums played', value=str(music_data['album_count']), category='music')
				prop.icon = 'play-circle'
				if 'discovery' in music_data:
					if 'albums' in music_data['discovery']:
						prop.description = str(len(music_data['discovery']['albums'])) + ' albums discovered'
				prop.save()

