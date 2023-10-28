from background_task import background
from django.conf import settings
from viewer.eventcollage import make_collage
from tempfile import NamedTemporaryFile
import datetime, pytz, os, random

from viewer.models import LifeReport, Event
from viewer.functions.utils import *
from viewer.report_styles import DefaultReport, ModernReport
from viewer.reporting import generate_report_travel, generate_report_photos, generate_report_people, generate_report_comms, generate_report_music, generate_report_movies

def photo_collage_upload_location(instance, filename):
	return 'collages/photo_collage_' + str(instance.pk) + '.jpg'

@background(schedule=0, queue='reports')
def generate_staticmap(event_id):
	"""
	Generates a static map (ie an image depicting a map) for an Event, if one does not already exist. Requires all relevant OpenStreetMap settings to be set.

	:param event_id: The ID (primary key) of the Event for which to create a static map.
	"""
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
	"""
	Generates one or more PhotoCollage objects for an Event object, assuming that some photos exist that were taken within that particular timeframe.

	:param event_id: The ID (primary key) of the Event for which to create PhotoCollages.
	"""
	try:
		max_photos = settings.PHOTO_COLLAGE_MAX_PHOTOS
	except:
		max_photos = 15
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
		if os.path.exists(photo_path):
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
def generate_life_event_photo_collages(event_id):
	"""
	Ensures all sub-events within a life event have PhotoCollages generated. Iterates sub-events looking for potential candidates, and fires a `generate_photo_collages` task for each one.

	:param event_id: The ID (primary key) of the Event of type 'life_event' for which to create PhotoCollages.
	"""
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
def generate_report_wordcloud(reportid):
	"""
	Generates a word cloud for a LifeReport object, using any text we can find within (event descriptions, messages, etc).

	:param reportid: The ID (primary key) of the report of which to create the word cloud
	"""
	report = LifeReport.objects.get(id=reportid)
	if report.cached_wordcloud:
		report.cached_wordcloud.delete()
	im = report.wordcloud()

@background(schedule=0, queue='reports')
def generate_report(title, year, options, style='default', pdf=True):
	"""
	A background task for generating a LifeReport object

	:param title: A descriptive title for the report (eg "The Year I Got Married")
	:param year: The calendar year with which to make a report
	:param options: A dict containing some options for generating the report
	:param style: The graphical style of the report, currently only applies to the printable PDF version of it
	:param pdf: True if we want the function to queue a `generate_report_pdf` task after completing, False if not
	"""

	tz = pytz.timezone(settings.TIME_ZONE)
	dts = tz.localize(datetime.datetime(year, 1, 1, 0, 0, 0))
	dte = tz.localize(datetime.datetime(year, 12, 31, 23, 59, 59))

	now = pytz.UTC.localize(datetime.datetime.utcnow())
	report = LifeReport(label=title, style=style, year=year)
	report.options = json.dumps(options)
	report.save()

	try:
		letterboxd_username = settings.LETTERBOXD_USERNAME
	except:
		letterboxd_username = ''
	try:
		moonshine_url = settings.MOONSHINE_URL
	except:
		moonshine_url = ''

	generate_report_people(report, dts, dte)
	generate_report_travel(report, dts, dte)
	generate_report_comms(report, dts, dte)
	generate_report_photos(report, dts, dte)
	generate_report_music(report, dts, dte, moonshine_url)
	generate_report_movies(report, letterboxd_username)

	subevents = []
	report.refresh_events()

	for event in report.events.filter(type='life_event').order_by('start_time'):
		for e in event.subevents():
			if e in subevents:
				continue
			subevents.append(e)
			if e.photos().count() > 5:
				if e.photo_collages.count() == 0:
					generate_photo_collages(e.pk)
			if not(e.cached_staticmap):
				if e.geo:
					if ((e.description != '') & (e.geo != '')):
						generate_staticmap(e.pk)

	for event in report.events.exclude(type='life_event').order_by('start_time'):
		if event in subevents:
			continue
		if event.photos().count() > 5:
			if event.photo_collages.count() == 0:
				generate_photo_collages(event.pk)
		if not(event.cached_staticmap):
			if event.geo:
				if ((event.description != '') & (event.geo != '')):
					generate_staticmap(event.pk)

	if options['wordcloud']:
		generate_report_wordcloud(report.id)

	if pdf:
		generate_report_pdf(report.id)

	return report

@background(schedule=0, queue='reports')
def generate_report_pdf(reportid, override_style=''):
	"""
	Creates a printable PDF report 'book' based on a LifeReport object

	:param reportid: The ID (primary key) of the report of which to create the PDF file
	:param override_style: The style of the report is normally selected at the creation time of the LifeReport, but can also be set here.
	"""
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
	filename = os.path.join(settings.MEDIA_ROOT, 'reports', 'report_' + str(report.id) + '_' + str(report.year) + '.pdf')
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

