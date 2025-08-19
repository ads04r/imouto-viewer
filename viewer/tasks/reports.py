from background_task import background
from django.conf import settings
from django.core.files import File
from tempfile import NamedTemporaryFile
from PIL import Image
from io import BytesIO
import datetime, pytz, os, random

from viewer.models import Event, Year, create_or_get_year, Photo, PhotoCollage
from viewer.reporting.generation import generate_year_travel, generate_year_photos, generate_year_comms, generate_year_music, generate_year_movies, generate_year_health
from viewer.reporting.pdf import generate_year_pdf
from viewer.reporting.styles import ImoutoMinimalistReportStyle
from viewer.functions.file_uploads import photo_collage_upload_location, year_pdf_upload_location
from viewer.functions.utils import choking
from viewer.eventcollage import make_collage
from django.contrib.auth.models import User

import logging
logger = logging.getLogger(__name__)

@background(schedule=0, queue='reports')
def generate_staticmap(event_id):
	"""
	Generates a static map (ie an image depicting a map) for an Event, if one does not already exist. Requires all relevant OpenStreetMap settings to be set.

	:param event_id: The ID (primary key) of the Event for which to create a static map.
	"""
	try:
		event = Event.objects.get(pk=event_id)
	except:
		return False # The event has been deleted since this task was scheduled.
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
def generate_event_photo_collage(event_id, photo_ids):

	if choking():
		# If load average is high, reschedule in 5 minutes time
		generate_event_photo_collage(event_id, photo_ids, schedule=300)
		return

	try:
		event = Event.objects.get(pk=event_id)
	except:
		logger.error("Could not load event " + str(event_id))
		return []
	if event.type == 'life_event':
		return []

	photos = []
	tempphotos = []

	im = Image.new(mode='RGB', size=(10, 10))
	blob = BytesIO()
	im.save(blob, 'JPEG')

	collage = PhotoCollage(event=event)
	collage.save()
	collage.image.save(photo_collage_upload_location(collage, 'collage.jpg'), File(blob), save=False)
	for photo in Photo.objects.filter(user=event.user, pk__in=photo_ids):

		photo_path = str(photo.file.path)
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
		collage.photos.add(photo)

	collage.save()
	make_collage(collage.image.path, photos, 2400, 3543)

	for photo in tempphotos:
		os.remove(photo)

@background(schedule=0, queue='reports')
def generate_photo_collages(event_id):
	"""
	Generates one or more PhotoCollage objects for an Event object, assuming that some photos exist that were taken within that particular timeframe.

	:param event_id: The ID (primary key) of the Event for which to create PhotoCollages.
	"""
	try:
		max_photos = settings.PHOTO_COLLAGE_MAX_PHOTOS
	except:
		max_photos = 10
	min_photos = 2

	try:
		event = Event.objects.get(pk=event_id)
	except:
		logger.error("Could not load event " + str(event_id))
		return []
	if event.type == 'life_event':
		return []

	event.photo_collages.all().delete()
	photos = []
	for photo in Photo.objects.filter(user=event.user, time__gte=event.start_time, time__lte=event.end_time).order_by("?")[0:(max_photos * 5)]:
		if photo.pk in photos:
			continue
		photos.append(photo.pk)

	if len(photos) < min_photos:
		return []

	delay = 60
	while len(photos) > 0:

		thisphotos = photos[0:max_photos]
		photos = photos[max_photos:]

		generate_event_photo_collage(event.pk, thisphotos, schedule=delay)
		delay = delay + 3600

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
def generate_year_wordcloud(user_id, year):
	"""
	Generates a word cloud for a Year object, using any text we can find within (event descriptions, messages, etc).

	:param year: The year of which to create the word cloud
	"""
	report = Year.objects.get(user__pk=user_id, year=year)
	if report.cached_wordcloud:
		report.cached_wordcloud.delete()
	report.wordcloud()

@background(schedule=0, queue='reports')
def generate_report(user_id, title, year):
	"""
	A background task for generating statistics for a year

	:param title: A descriptive title for the report (eg "The Year I Got Married")
	:param year: The calendar year with which to make a report
	"""

	user = User.objects.get(pk=user_id)
	report = create_or_get_year(user, year)
	if report.cached_pdf:
		report.cached_pdf.delete()
	if len(title) > 0:
		report.caption = title
		report.save(update_fields=['caption'])
	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(report.year, 1, 1, 0, 0, 0))
	dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(report.year + 1, 1, 1, 0, 0, 0)) - datetime.timedelta(seconds=1)

	report.report_prc = 0
	report.save(update_fields=['report_prc'])

	try:
		letterboxd_username = settings.LETTERBOXD_USERNAME
	except:
		letterboxd_username = ''
	try:
		moonshine_url = settings.MOONSHINE_URL
	except:
		moonshine_url = ''

	generate_year_health(report)
	report.report_prc = 10
	report.save(update_fields=['report_prc'])
	generate_year_travel(report)
	report.report_prc = 20
	report.save(update_fields=['report_prc'])
	generate_year_comms(report)
	report.report_prc = 30
	report.save(update_fields=['report_prc'])
	generate_year_photos(report)
	report.report_prc = 40
	report.save(update_fields=['report_prc'])
	generate_year_music(report, moonshine_url)
	report.report_prc = 50
	report.save(update_fields=['report_prc'])
	generate_year_movies(report, letterboxd_username)
	report.report_prc = 60
	report.save(update_fields=['report_prc'])

	event_count = report.events.count()
	increment = int(30.0 / float(event_count * 2))
	for event in report.events.order_by('start_time'):
		if event.photos().count() > 5:
			if event.photo_collages.count() == 0:
				generate_photo_collages(event.pk)
		report.report_prc = report.report_prc + increment
		report.save(update_fields=['report_prc'])
		if not(event.cached_staticmap):
			if event.geo:
				if ((event.description != '') & (event.geo != '')):
					generate_staticmap(event.pk)
		report.report_prc = report.report_prc + increment
		report.save(update_fields=['report_prc'])

	generate_year_wordcloud(year)

	report.report_prc = 100
	report.save(update_fields=['report_prc'])

@background(schedule=0, queue='reports')
def generate_report_pdf(year):
	"""
	A background task for generating a PDF from a Year object

	:param year: The calendar year with which to make a report
	"""

	report = create_or_get_year(year)
	if report.cached_pdf:
		report.cached_pdf.delete()
		report.save(update_fields=['cached_pdf'])
	path = os.path.join(settings.MEDIA_ROOT, year_pdf_upload_location(report, ''))
	generate_year_pdf(year, path, ImoutoMinimalistReportStyle)
	report.cached_pdf = path
	report.save(update_fields=['cached_pdf'])

@background(schedule=0, queue='reports')
def update_year(year):
	"""
	Can be run occasionally throughout a year to ensure things like photo collages and static maps are kept up to date.
	The idea is that the actual year report generation time is kept to a minimum if we do a lot of the heavy lifting as
	the year progresses.

	:param year: The year to update. Normally the current year, but doesn't have to be.
	"""
	for event in year.events.filter(user=year.user):
		if event.photos().count() == 0:
			continue
		if event.photo_collages.count() > 0:
			continue
		generate_photo_collages(event.pk)
	for event in year.events.filter(user=year.user).exclude(geo=None).exclude(geo='').exclude(description=''):
		try:
			f = event.cached_staticmap.file
		except:
			f = None
		if not f is None:
			continue
		generate_staticmap(event.pk)
	for month in year.months.order_by('month'):
		if month.this_month:
			break
		event = month.longest_journey
		if event is None:
			continue
		generate_staticmap(event.pk)
