from django.core.management.base import BaseCommand
from django.conf import settings
from viewer.models import DataReading, Event
import os, sys, datetime, shutil, sqlite3, pytz

class Command(BaseCommand):
	"""
	Command for importing sleep and step data from a Pebble smartwatch's database file. This file needs to be copied from the Pebble Android app's data directory.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="A pebble data file, copied from the data directory of the Pebble Android app.")

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])
		temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
		file = os.path.join(temp_dir, str(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")) + "_" + os.path.basename(uploaded_file))

		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)

		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			os.remove(file)
			sys.exit(1)

		if not os.path.exists(temp_dir):
			os.makedirs(temp_dir)
		shutil.copyfile(uploaded_file, file)

		try:
			conn = sqlite3.connect(file)
		except:
			sys.stderr.write(self.style.ERROR("File error: could not open '" + uploaded_file + "'\n"))
			os.remove(file)
			sys.exit(1)

		last_event_1 = Event.objects.filter(type='journey', caption__endswith='km walk').order_by('-start_time')[0]
		last_event_2 = Event.objects.filter(type='journey', caption='Walk').order_by('-start_time')[0]
		last_entry = DataReading.objects.filter(type='pebble-app-activity').order_by('-start_time')[0]
		last_step = DataReading.objects.filter(type='step-count').order_by('-start_time')[0]

		if last_event_1.start_time > last_event_2.start_time:
			last_event = last_event_1
		else:
			last_event = last_event_2

		c = conn.cursor()

		cache.delete('dashboard')
		sys.stdout.write("Parsing Pebble file...\n")

		# This bit looks for activities, specifically 'long walk' and 'sleep' events.

		query = "SELECT start_utc_secs, end_utc_secs, type FROM activity_sessions WHERE start_utc_secs>='" + str(int(last_entry.start_time.timestamp())) + "' ORDER BY start_utc_secs ASC;"
		if last_event.start_time < last_entry.start_time:
			query = "SELECT start_utc_secs, end_utc_secs, type FROM activity_sessions WHERE start_utc_secs>='" + str(int(last_event.start_time.timestamp())) + "' ORDER BY start_utc_secs ASC;"
		try:
			res = c.execute(query)
		except sqlite3.DatabaseError:
			sys.stderr.write(self.style.ERROR("File error: '" + uploaded_file + "' is malformed\n"))
			os.remove(file)
			sys.exit(1)

		for row in res:
			dts = datetime.datetime.fromtimestamp(int(row[0]), tz=pytz.UTC)
			dte = datetime.datetime.fromtimestamp(int(row[1]), tz=pytz.UTC)
			type = 'pebble-app-activity'
			value = int(row[2])
			try:
				dp = DataReading.objects.get(type=type, start_time=dts, end_time=dte)
			except:
				dp = DataReading(start_time=dts, end_time=dte, type=type, value=value)
				dp.save()

		# This bit counts steps and adds them as DataReadings

		step_count = 0
		try:
			res = c.execute("SELECT date_utc_secs, step_count FROM minute_samples WHERE date_utc_secs>='" + str(int(last_step.start_time.timestamp())) + "';")
		except sqlite3.DatabaseError:
			sys.stderr.write(self.style.ERROR("File error: '" + uploaded_file + "' is malformed\n"))
			os.remove(file)
			sys.exit(1)

		for row in res:
			dts = datetime.datetime.fromtimestamp(int(row[0]), tz=pytz.UTC)
			dte = datetime.datetime.fromtimestamp((int(row[0]) + 59), tz=pytz.UTC)
			steps = row[1]
			type = 'step-count'
			if steps == 0:
				continue
			try:
				dp = DataReading.objects.get(type=type, start_time=dts, end_time=dte)
			except:
				dp = DataReading(start_time=dts, end_time=dte, type=type, value=steps)
				dp.save()
				step_count = step_count + steps

		if step_count > 0:
			sys.stderr.write(self.style.SUCCESS("Added " + str(step_count) + " steps\n"))

		os.remove(file)
		cache.delete('dashboard')
