from background_task import background
from django.db.models import Count
from .models import LifeReport, Event
from .functions import *
from .report_styles import DefaultReport, ModernReport
from xml.dom import minidom
from tzlocal import get_localzone
from viewer.eventcollage import make_collage
from tempfile import NamedTemporaryFile
import datetime, pytz, os, random
from .reporting import generate_report_travel, generate_report_photos, generate_report_people, generate_report_comms, generate_report_music

def photo_collage_upload_location(instance, filename):
	return 'collages/photo_collage_' + str(instance.pk) + '.jpg'

@background(schedule=0, queue='reports')
def generate_life_event_photo_collages(event_id):
	""" A task for ensuring all sub-events within a life event have photo collages generated. """

	max_photos = 30
	min_photos = 2

	ret = []
	event = Event.objects.get(pk=event_id)
	if event.type != 'life_event':
		return ret

	for e in event.subevents():
		photos = e.photos()
		if len(photos) <= min_photos:
			continue
		if e.photo_collages.count() == 0:
			generate_photo_collages(e.pk)
			ret.append(e.pk)

	return ret

@background(schedule=0, queue='reports')
def generate_staticmap(event_id):
	""" A background task for generating a static map for an event"""
	event = Event.objects.get(pk=event_id)
	if event.cached_staticmap:
		return False # There's already a map.
	if not(event.geo):
		return False # There's no geometry, so we can't generate a map.

	try:
		im = event.staticmap()
	except:
		return False # It threw an exception. Ignore it.
	return True

@background(schedule=0, queue='reports')
def generate_photo_collages(event_id):
	""" A background task for generating photo collages"""

	max_photos = 30
	min_photos = 2

	event = Event.objects.get(pk=event_id)
	if event.type == 'life_event':
		return []
	event.photo_collages.all().delete()
	photos = []
	tempphotos = []
	for photo in Photo.objects.filter(time__gte=event.start_time, time__lte=event.end_time).order_by("?")[0:(max_photos * 5)]:
		photo_path = str(photo.file.path)
		if photo_path in photos:
			continue
		if len(photo.picasa_info()) == 0:
			photos.append(photo_path)
		else:
			tf = NamedTemporaryFile(delete=False)
			im = photo.image()
			try:
				im.save(tf, format='JPEG')
				photos.append(tf.name)
				tempphotos.append(tf.name)
			except:
				photos.append(photo_path)

	if len(photos) < min_photos:
		return []

	random.shuffle(photos)
	ret = []

	while len(photos) > 0:

		im = Image.new(mode='RGB', size=(10, 10))
		blob = BytesIO()
		im.save(blob, 'JPEG')

		collage = PhotoCollage(event=event)
		collage.save()
		collage.image.save(photo_collage_upload_location(collage, 'collage.jpg'), File(blob), save=False)
		for photo in Photo.objects.filter(time__gte=event.start_time, time__lte=event.end_time):
			collage.photos.add(photo)
		collage.save()
		thisphotos = photos[0:max_photos]
		filename = make_collage(collage.image.path, thisphotos, 2400, 3543)
		ret.append(filename)

		photos = photos[max_photos:]

	for photo in tempphotos:
		os.remove(photo)

	return ret

@background(schedule=0, queue='reports')
def generate_report_wordcloud(reportid):
	""" A background task for generating word clouds for LifeReport objects"""
	report = LifeReport.objects.get(id=reportid)
	if report.cached_wordcloud:
		report.cached_wordcloud.delete()
	im = report.wordcloud()

@background(schedule=0, queue='reports')
def generate_report(title, dss, dse, options, type='year', style='default', moonshine_url='', pdf=True):
	""" A background task for generating LifeReport objects"""

	dts = datetime.datetime.strptime(dss, "%Y-%m-%d %H:%M:%S %z")
	dte = datetime.datetime.strptime(dse, "%Y-%m-%d %H:%M:%S %z")

	tz = get_localzone()
	now = pytz.UTC.localize(datetime.datetime.utcnow())
	report = LifeReport(label=title, type=type, style=style, modified_date=now)
	report.options = json.dumps(options)
	report.save()
	subevents = []

	for event in Event.objects.filter(type='life_event', start_time__lte=dte, end_time__gte=dts).order_by('start_time'):
		report.events.add(event)
		if event.location:
			report.locations.add(event.location)
		for e in event.subevents():
			if e in subevents:
				continue
			subevents.append(e)
			if e.photo_collages.count() == 0:
				generate_photo_collages(e.pk)
			if not(e.cached_staticmap):
				if e.geo:
					if e.description != '':
						generate_staticmap(e.pk)

	for event in Event.objects.filter(start_time__lte=dte, end_time__gte=dts).order_by('start_time').exclude(type='life_event'):
		if event.location:
			report.locations.add(event.location)
		if event in subevents:
			continue
		if event.photos().count() > 5:
			report.events.add(event)
			if event.photo_collages.count() == 0:
				generate_photo_collages(event.pk)
		if not(event.cached_staticmap):
			if event.geo:
				generate_staticmap(event.pk)
		if event.description is None:
			continue
		if event.description == '':
			continue
		report.events.add(event)

	generate_report_people(report, dts, dte)
	generate_report_travel(report, dts, dte)
	generate_report_comms(report, dts, dte)
	generate_report_photos(report, dts, dte)
	generate_report_music(report, dts, dte, moonshine_url)

	if options['wordcloud']:
		generate_report_wordcloud(report.id)

	if pdf:
		generate_report_pdf(report.id)

	return report

@background(schedule=0, queue='reports')
def generate_report_pdf(reportid, override_style=''):
	""" A background task for creating a PDF report based on a LifeReport object """

	try:
		report = LifeReport.objects.get(id=reportid)
	except:
		return None # Entirely possible that the report has been deleted before this function gets triggered

	if report is None:
		return None

	style = override_style
	if style == '':
		style = report.style
	options = json.loads(report.options)
	filename = os.path.join(settings.MEDIA_ROOT, 'reports', 'report_' + str(report.id) + '.pdf')
	pages = report.pages()

	if style == 'modern':
		pdf = ModernReport()
	else:
		pdf = DefaultReport()
	for page in pages:
		if page['type'] == 'title':
			title = ''
			subtitle = ''
			if 'title' in page:
				title = page['title']
			if 'subtitle' in page:
				subtitle = page['subtitle']
			pdf.add_title_page(title, subtitle)
		if page['type'] == 'image':
			file = page['image']
			ext = file.split('.')[-1]
			if os.path.exists(file):
				caption = ''
				if 'text' in page:
					caption = page['text']
				pdf.add_image_page(page['image'], format=ext, caption=caption)
		if page['type'] == 'items':
			pdf.add_row_items_page(page['data'])
		if page['type'] == 'feature':
			image = ''
			if 'image' in page:
				image = page['image']
			pdf.add_feature_page(page['title'], page['description'], image)
		if page['type'] == 'stats':
			pdf.add_stats_page(page['title'], page['data'])
		if page['type'] == 'grid':
			pdf.add_grid_page(page['title'], page['data'])
		if page['type'] == 'chart':
			if 'description' in page:
				pdf.add_chart_page(page['title'], page['description'], page['data'])
			else:
				pdf.add_chart_page(page['title'], '', page['data'])

	pdf.output(filename, 'F')
	report.pdf = filename
	report.save()

	return report

