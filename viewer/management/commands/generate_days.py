from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.db.models import Max, Min
from viewer.models import Day, DataReading
import os, sys, datetime, shutil, sqlite3, pytz

class Command(BaseCommand):
	"""
	Command for generating (or regenerating) day objects from the first event to the present.
	"""
	def handle(self, *args, **kwargs):

		if DataReading.objects.count() == 0:
			sys.exit(0) # No data, so nothing to do!

		data = DataReading.objects.aggregate(min=Min('start_time'), max=Max('end_time'))
		dts = data['min'].date()
		dte = data['max'].date()
		created = 0
		updated = 0

		sys.stderr.write(self.style.WARNING("Working on " + str(int((dte - dts).total_seconds() / 86400)) + " days of data.\n"))

		dt = dts
		while dt < dte:
			try:
				day = Day.objects.get(date=dt)
				day.cached_heart_information = None
				day.cached_sleep_information = None
				updated = updated + 1
			except:
				day = Day(date=dt)
				created = created + 1
			s = day.get_sleep_information()
			h = day.get_heart_information()

			sys.stderr.write(str(dt.strftime("%Y - %m - %d")) + "\r")

			dt = dt + datetime.timedelta(days=1)

		sys.stderr.write(self.style.SUCCESS("Created " + str(created) + " new Day objects.\n"))
		sys.stderr.write(self.style.SUCCESS("Updated " + str(updated) + " existing Day objects.\n"))

