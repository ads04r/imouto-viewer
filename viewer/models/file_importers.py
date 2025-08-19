from django.db import models
from django.contrib.auth.models import User
import os, datetime, pytz

import logging
logger = logging.getLogger(__name__)

class WatchedDirectory(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	path = models.CharField(max_length=1024, null=False)
	recursive = models.BooleanField(default=False)
	file_regex = models.CharField(max_length=512, null=True, blank=True)
	last_check = models.DateTimeField()
	check_interval = models.IntegerField(default=300)
	importer = models.SlugField(max_length=100)
	source = models.SlugField(max_length=32, default='', blank=True)
	def __files_in_directory(self, path=None):
		scan_path = path
		ret = []
		if scan_path is None:
			scan_path = self.path
		if not(os.path.exists(scan_path)):
			return []
		for f in os.listdir(scan_path):
			check_path = os.path.join(scan_path, f)
			if os.path.isdir(check_path):
				continue
			ret.append(check_path)
		if self.recursive:
			for d in os.listdir(scan_path):
				check_path = os.path.join(scan_path, d)
				if not(os.path.isdir(check_path)):
					continue
				ret = ret + self.__files_in_directory(check_path)
		return ret
	@property
	def label(self):
		parse = self.path.strip('/').split('/')
		return parse[-1]
	@property
	def exists(self):
		return os.path.exists(self.path)
	@property
	def needs_check(self):
		next_check = self.last_check + datetime.timedelta(seconds=self.check_interval)
		return (next_check < pytz.utc.localize(datetime.datetime.utcnow()))
	@property
	def last_upload(self):
		files = self.known_files.exclude(import_time=None)
		ret = files.order_by('-import_time')
		if ret.count == 0:
			return None
		return ret.first()
	@property
	def unimported_files(self):
		if not(os.path.exists(self.path)):
			return []
		ret = []
		ignore = []
		for f in self.known_files.all():
			if f.path in ignore:
				continue
			if f.exists:
				if not(f.path in ret):
					if f.import_time is None:
						ret.append(f.path)
					else:
						file_size = os.path.getsize(f.path)
						modified_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(f.path)))
						if not((f.file_size == file_size) & (f.modified_time == modified_time)):
							ret.append(f.path)
			ignore.append(f.path)
		for fn in self.__files_in_directory():
			if fn in ignore:
				continue
			if fn in ret:
				continue
			if fn.startswith(self.path):
				modified_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(fn)))
				file_size = os.path.getsize(fn)
				rel_path = fn[(len(self.path) + 1):]
				file_object = ImportedFile(user=self.user, relative_path=rel_path, modified_time=modified_time, watched_directory=self, file_size=file_size)
				file_object.save()
				ret.append(fn)
		return ret
	def __str__(self):
		return self.path
	class Meta:
		verbose_name = "watched directory"
		verbose_name_plural = "watched directories"

class ImportedFile(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	relative_path = models.CharField(max_length=512, null=False)
	watched_directory = models.ForeignKey(WatchedDirectory, on_delete=models.CASCADE, related_name='known_files')
	modified_time = models.DateTimeField()
	import_time = models.DateTimeField(null=True)
	file_size = models.IntegerField(default=0)
	earliest_timestamp = models.DateTimeField(null=True, blank=True, default=None)
	latest_timestamp = models.DateTimeField(null=True, blank=True, default=None)
	activity = models.CharField(max_length=64, null=True, blank=True)
	@property
	def path(self):
		return os.path.join(self.watched_directory.path, self.relative_path)
	@property
	def exists(self):
		return os.path.exists(os.path.join(self.watched_directory.path, self.relative_path))
	def __str__(self):
		return self.relative_path
	class Meta:
		verbose_name = "imported file"
		verbose_name_plural = "imported files"

