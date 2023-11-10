from viewer.models import WatchedDirectory
import datetime, pytz, os

def get_all_files_to_upload():

	ret = []
	for wd in WatchedDirectory.objects.all():
		for fn in wd.unimported_files:
			for f in wd.known_files.all():
				if f.path == fn:
					modified_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(fn)))
					file_size = os.path.getsize(fn)
					if((f.modified_time == modified_time) & (f.file_size == file_size)):
						ret.append(fn)
					else:
						f.modified_time = modified_time
						f.file_size = file_size
						f.import_time = None
						f.save()
	return ret

