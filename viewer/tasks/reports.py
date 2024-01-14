from background_task import background
from django.conf import settings
from tempfile import NamedTemporaryFile
import datetime, pytz, os, random, json

from viewer.models import Event, Year, create_or_get_year
from viewer.functions.utils import *
from viewer.reporting.generation import generate_year_travel, generate_year_photos, generate_year_comms, generate_year_music, generate_year_movies, generate_year_health
from viewer.reporting.pdf import generate_year_pdf
from viewer.functions.file_uploads import photo_collage_upload_location, year_pdf_upload_location
from viewer.eventcollage import make_collage
from background_task.models import Task

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
def generate_year_wordcloud(year):
	"""
	Generates a word cloud for a Year object, using any text we can find within (event descriptions, messages, etc).

	:param year: The year of which to create the word cloud
	"""
	report = Year.objects.get(year=year)
	if report.cached_wordcloud:
		report.cached_wordcloud.delete()
	report.wordcloud()

@background(schedule=0, queue='reports')
def generate_report(title, year):
	"""
	A background task for generating statistics for a year

	:param title: A descriptive title for the report (eg "The Year I Got Married")
	:param year: The calendar year with which to make a report
	"""

	report = create_or_get_year(year)
	if len(title) > 0:
		report.caption = title
		report.save(update_fields=['caption'])
	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(report.year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(report.year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)

	try:
		letterboxd_username = settings.LETTERBOXD_USERNAME
	except:
		letterboxd_username = ''
	try:
		moonshine_url = settings.MOONSHINE_URL
	except:
		moonshine_url = ''

	generate_year_health(report)
	generate_year_travel(report)
	generate_year_comms(report)
	generate_year_photos(report)
	generate_year_music(report, moonshine_url)
	generate_year_movies(report, letterboxd_username)

	for event in report.events.order_by('start_time'):
		if event.photos().count() > 5:
			if event.photo_collages.count() == 0:
				generate_photo_collages(event.pk)
		if not(event.cached_staticmap):
			if event.geo:
				if ((event.description != '') & (event.geo != '')):
					generate_staticmap(event.pk)

	generate_year_wordcloud(year)
	generate_report_pdf(year)

@background(schedule=0, queue='reports')
def generate_report_pdf(year):
	"""
	A background task for generating a PDF from a Year object

	:param year: The calendar year with which to make a report
	"""

	for task in Task.objects.filter(task_name__contains='generate_report_pdf', queue='reports'):
		task_year = json.loads(task.task_params)[0][0]
		if task_year == year:
			return False # Don't start another task if one is already queued or running

	report = create_or_get_year(year)
	if report.cached_pdf:
		report.cached_pdf.delete()
		report.save(update_fields=['cached_pdf'])
	path = os.path.join(settings.MEDIA_ROOT, year_pdf_upload_location(year, ''))
	generate_year_pdf(year, path)
	report.cached_pdf = path
	report.save(update_fields=['cached_pdf'])
