from background_task import background
import datetime, pytz, os

from background_task.models import Task
from viewer.models import Photo, WatchedDirectory
from viewer.functions.locations import fill_country_cities, fill_location_cities
from viewer.functions.location_manager import get_location_manager_report_queue

@background(schedule=0, queue='process')
def fill_cities():
	"""
	Uses an OSM API to determine the cities that exist within the countries visited, and matches them
	to locations where possible.
	"""
	if Task.objects.filter(queue='process', task_name__icontains='tasks.fill_cities').count() > 1:
		return # If there's already an instance of this task running or queued, don't start another.
	if len(get_location_manager_report_queue()) > 0:
		fill_cities(schedule=60) # If there are tasks in the location manager, hold back until they finish
		return
	fill_country_cities()
	fill_location_cities()

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
