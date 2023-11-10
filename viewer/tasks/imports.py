import datetime, pytz, os
from background_task import background

from background_task.models import Task
from viewer.models import WatchedDirectory
from viewer.functions.location_manager import get_location_manager_report_queue
from viewer.importers.upload import import_fit
from viewer.importers.location import upload_file

@background(schedule=0, queue='process')
def check_watched_directories():
	"""
	Iterates through all the watched directories and begins an import for each new file found.
	"""
	if Task.objects.filter(queue='process', task_name__icontains='tasks.imports.check_watched_directories').count() > 1:
		return # If there's already an instance of this task running or queued, don't start another.
	if len(get_location_manager_report_queue()) > 0:
		check_watched_directories(schedule=60) # If there are tasks in the location manager, hold back until they finish
		return

	ret = []
	for wd in WatchedDirectory.objects.all():
		for fn in wd.unimported_files:
			for f in wd.known_files.all():
				if f.path == fn:
					modified_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(fn)))
					file_size = os.path.getsize(fn)
					if((f.modified_time == modified_time) & (f.file_size == file_size)):
						f.import_time = pytz.utc.localize(datetime.datetime.utcnow())
						f.save()
						ret.append([fn, f.importer, f.source])
					else:
						f.modified_time = modified_time
						f.file_size = file_size
						f.import_time = None
						f.save()
	for fn in ret:
		if fn[1] == 'fit':
			upload_file(fn[0], fn[2])
			import_fit(fn[0])
		if fn[1] == 'gpx':
			upload_file(fn[0], fn[2])
