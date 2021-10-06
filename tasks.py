from background_task import background
from .models import *
from .functions import *
from .report_styles import *
from xml.dom import minidom
from tzlocal import get_localzone
import datetime, pytz, os

@background(schedule=0, queue='reports')
def generate_report(title, dss, dse, type='year', style='default', moonshine_url='', pdf=True):
	""" A background task for generating LifeReport objects"""

	dts = datetime.datetime.strptime(dss, "%Y-%m-%d %H:%M:%S %z")
	dte = datetime.datetime.strptime(dse, "%Y-%m-%d %H:%M:%S %z")

	tz = get_localzone()
	now = pytz.UTC.localize(datetime.datetime.utcnow())
	report = LifeReport(label=title, type=type, style=style, modified_date=now)
	report.save()
	subevents = []
	for event in Event.objects.filter(type='life_event', start_time__lte=dte, end_time__gte=dts).order_by('start_time'):
		report.events.add(event)
		if event.location:
			report.locations.add(event.location)
		for person in event.people.all():
			report.people.add(person)
		for e in event.subevents():
			if e in subevents:
				continue
			subevents.append(e)

	for event in Event.objects.filter(start_time__lte=dte, end_time__gte=dts).order_by('start_time').exclude(type='life_event'):
		if event.location:
			report.locations.add(event.location)
		for person in event.people.all():
			report.people.add(person)
		if event in subevents:
			continue
		if event.description != '':
			report.events.add(event)
		if event.photos().count() > 5:
			report.events.add(event)

	photos = Photo.objects.filter(time__gte=dts, time__lte=dte).count()
	photos_gps = Photo.objects.filter(time__gte=dts, time__lte=dte).exclude(lat=None).exclude(lon=None).count()
	photos_people = Photo.objects.filter(time__gte=dts, time__lte=dte).annotate(Count('people')).exclude(people__count=0).count()

	prop = report.addproperty(key='Photos Taken', value=photos, category='photos')
	prop.icon = 'camera'
	prop.save()

	prop = report.addproperty(key='Photos with GPS', value=photos_gps, category='photos')
	prop.icon = 'map-marker'
	prop.save()

	prop = report.addproperty(key='Photos of People', value=photos_people, category='photos')
	prop.icon = 'user'
	prop.save()

	countries = report.countries().count()
	if countries > 1:
		prop = report.addproperty(key='Countries Visited', value=(countries - 1), category='travel')
		prop.icon = 'globe'
		prop.save()

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
		smsg1 = LifeReportGraph(key='SMS Send vs SMS Received', type='donut', description='', icon='', report=report, category='communication', data=json.dumps([["Sent", "Received"],[sms_sent, sms_recv]]))
		smsg1.save()

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


	if pdf:
		generate_report_pdf(report.id, style)

	return report

@background(schedule=0, queue='reports')
def generate_report_pdf(reportid, style):
	""" A background task for creating a PDF report based on a LifeReport object """

	report = LifeReport.objects.get(id=reportid)
	year = report.events.order_by('start_time').first().end_time.year
	im = report.wordcloud()
	filename = os.path.join(settings.MEDIA_ROOT, 'reports', 'report_' + str(report.id) + '.pdf')
	pdf = DefaultReport()
	pdf.add_title_page(str(report.year()), report.label)
	if(report.cached_wordcloud):
		pdf.add_image_page(str(report.cached_wordcloud.file))
	categories = []
	for prop in report.properties.all():
		if prop.category in categories:
			continue
		categories.append(prop.category)
	if report.people.count() > 0:
		pdf.add_people_page(report.people, report.properties.filter(category='people'))
	for category in categories:
		if category == 'people':
			continue
		pdf.add_stats_category(category.capitalize(), report.properties.filter(category=category))
	for event in report.events.filter(type='life_event').order_by('start_time'):
		pdf.add_life_event_page(event)
	for i in range(1, 13):
		mts = datetime.datetime(year, i, 1, 0, 0, 0, tzinfo=pytz.UTC)
		if i == 12:
			mte = datetime.datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
		else:
			mte = datetime.datetime(year, i + 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
		mte = mte - datetime.timedelta(seconds=1)
		events = report.events.filter(end_time__gte=mts, start_time__lte=mte).order_by('start_time')
		pdf.add_month_page(i, events)
	pdf.output(filename, 'F')
	report.pdf = filename
	report.save()

	return report

