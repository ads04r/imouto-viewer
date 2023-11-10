from background_task import background
from django.conf import settings
import datetime, pytz, os

from background_task.models import Task
from viewer.functions.utils import *
from viewer.functions.locations import create_location_events, fill_country_cities, fill_location_cities
from viewer.functions.location_manager import get_location_manager_report_queue

@background(schedule=0, queue='process')
def check_watched_directories():
	"""
	Iterates through all the watched directories and begins an import for each new file found.
	"""
	if Task.objects.filter(queue='process', task_name__icontains='tasks.check_watched_directories').count() > 1:
		return # If there's already an instance of this task running or queued, don't start another.
	if len(get_location_manager_report_queue()) > 0:
		check_watched_directories(schedule=60) # If there are tasks in the location manager, hold back until they finish
		return

@background(schedule=0, queue='process')
def fill_cities():
	"""
	Uses an OSM API to determine the cities that exist within the countries visited, and matches them
	to locations where possible.
	"""
	if Task.objects.filter(queue='process', task_name__icontains='tasks.fill_cities').count() > 1:
		return # If there's already an instance of this task running or queued, don't start another.
	if len(get_location_manager_report_queue()) > 0:
		generate_location_events(min_duration=min_duration, schedule=60) # If there are tasks in the location manager, hold back until they finish
		return
	fill_country_cities()
	fill_location_cities()

@background(schedule=0, queue='process')
def generate_location_events(min_duration=300):
	"""
	Creates a set of location Events based on the no-movement periods generated by the Location Manager.

	:param min_duration: Doesn't create Events shorter than this many seconds. Good for avoiding creating 'stopped at a red light' Events.
	"""
	if Task.objects.filter(queue='process', task_name__icontains='tasks.generate_location_events').count() > 1:
		return # If there's already an instance of this task running or queued, don't start another.
	if len(get_location_manager_report_queue()) > 0:
		generate_location_events(min_duration=min_duration, schedule=60) # If there are tasks in the location manager, hold back until they finish
		return
	create_location_events(min_duration)

@background(schedule=0, queue='process')
def precache_photo_thumbnails(limit=200):
	"""
	Searches for all the Photos without a cached thumbnail, and queues a `precache_photo_thumbnail` task for each one.

	:param limit: The maximum number of tasks to be created. Defaults to 200 but can be adjusted depending on system resources.
	"""
	for photo in Photo.objects.filter(cached_thumbnail=None)[0:limit]:
		precache_photo_thumbnail(photo.id)

@background(schedule=0, queue='process')
def precache_photo_thumbnail(photo_id):
	"""
	Generates and caches a single Photo's thumbnail, for quicker page rendering later.

	:param photo_id: The ID (primary key) of the Photo to process.
	"""
	photo = Photo.objects.get(id=photo_id)
	try:
		im = photo.thumbnail(200)
	except:
		pass
