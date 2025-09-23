from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from viewer.models import DataReading, Event
import os, sys, datetime, shutil, sqlite3, pytz

class Command(BaseCommand):
	"""
	Command for importing sleep and step data from a Pebble smartwatch's database file. This file needs to be copied from the Pebble Android app's data directory.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-u", "--user", action="store", dest="user_id", required=True, help="which user are we working with?")
		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="A pebble data file, copied from the data directory of the Pebble Android app.")

	def handle(self, *args, **kwargs):

		try:
			user = User.objects.get(username=kwargs['user_id'])
		except:
			user = None
		if not user:
			sys.stderr.write(self.style.ERROR(str(kwargs['user_id']) + " is not a valid user on this system.\n"))
			sys.exit(1)

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

		last_events = []
		try:
			last_events.append(Event.objects.filter(user=user, type='journey', caption__endswith='km walk').order_by('-start_time')[0])
		except IndexError:
			pass
		try:
			last_events.append(Event.objects.filter(user=user, type='journey', caption='Walk').order_by('-start_time')[0])
		except IndexError:
			pass
			last_events.append(Event.objects.filter(user=user, type='journey', caption__startswith='Walking in ').order_by('-start_time')[0])
		except IndexError:
			pass
		try:
			last_events.append(Event.objects.filter(user=user, workout_categories__id='walking').order_by('-start_time')[0])
		except IndexError:
			pass
		try:
			last_events.append(Event.objects.filter(user=user, workout_categories__id='walk').order_by('-start_time')[0])
		except IndexError:
			pass
		try:
			last_events.append(Event.objects.filter(user=user, type='journey', transit_method__label__iexact='walking').order_by('-start_time')[0])
		except IndexError:
			pass
		last_entry = DataReading.objects.filter(user=user, type='pebble-app-activity').order_by('-start_time')[0]
		last_step = DataReading.objects.filter(user=user, type='step-count').order_by('-start_time')[0]
		if len(last_events) == 0:
			last_event = Event.objects.filter(user=user).order_by('-start_time')[0] # There should be at least one event. If not, we have bigger problems.
		else:
			last_event = sorted(last_events, reverse=True, key=lambda x: x.start_time)[0]

		c = conn.cursor()

		cache.delete('dashboard')

		# Check for database type; we support official Pebble app and Gadgetbridge

		db_type = ''
		query = "SELECT COUNT(name) FROM sqlite_master WHERE type='table' and name='activity_sessions';"
		c.execute(query)
		if c.fetchone()[0] == 1:
			sys.stderr.write(self.style.WARNING("Parsing Pebble file...\n"))
			db_type = 'pebble'
		query = "SELECT COUNT(name) FROM sqlite_master WHERE type='table' and name='PEBBLE_HEALTH_ACTIVITY_OVERLAY';"
		c.execute(query)
		if c.fetchone()[0] == 1:
			sys.stderr.write(self.style.WARNING("Parsing GadgetBridge file...\n"))
			db_type = 'gadgetbridge'

		if db_type == '': # Die if no compatible database found
			sys.stderr.write(self.style.ERROR("Cannot identify data file type. The file must be the database file from the official Pebble app, or an auto-dump file from GadgetBridge.\n"))
			os.remove(file)
			sys.exit(1)

		# This bit looks for activities, specifically 'long walk' and 'sleep' events.

		if db_type == 'pebble':
			query = "SELECT start_utc_secs, end_utc_secs, type FROM activity_sessions WHERE start_utc_secs>='" + str(int(last_entry.start_time.timestamp())) + "' ORDER BY start_utc_secs ASC;"
			if last_event.start_time < last_entry.start_time:
				query = "SELECT start_utc_secs, end_utc_secs, type FROM activity_sessions WHERE start_utc_secs>='" + str(int(last_event.start_time.timestamp())) + "' ORDER BY start_utc_secs ASC;"
		if db_type == 'gadgetbridge':
			query = "SELECT TIMESTAMP_FROM, TIMESTAMP_TO, RAW_KIND FROM PEBBLE_HEALTH_ACTIVITY_OVERLAY WHERE TIMESTAMP_FROM>='" + str(int(last_entry.start_time.timestamp())) + "' ORDER BY TIMESTAMP_FROM ASC;"
			if last_event.start_time < last_entry.start_time:
				query = "SELECT TIMESTAMP_FROM, TIMESTAMP_TO, RAW_KIND FROM PEBBLE_HEALTH_ACTIVITY_OVERLAY WHERE TIMESTAMP_FROM>='" + str(int(last_event.start_time.timestamp())) + "' ORDER BY TIMESTAMP_FROM ASC;"
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
			if ((value == 1) or (value == 2)):
				type = 'sleep'
			try:
				dp = DataReading.objects.get(user=user, type=type, start_time=dts, end_time=dte)
			except:
				dp = DataReading(user=user, start_time=dts, end_time=dte, type=type, value=value)
				dp.save()

		# Add 'awake' events between the 'sleep' events, for easier parsing later

		if DataReading.objects.filter(user=user, type='sleep').count() > 0:
			if DataReading.objects.filter(user=user, type='awake').count() == 0:
				dtmin = DataReading.objects.filter(user=user, type='sleep').order_by('start_time')[0].start_time
			else:
				dtmin = DataReading.objects.filter(user=user, type='awake').order_by('-end_time')[0].end_time
			sleeps = DataReading.objects.filter(user=user, type='sleep', value='1', start_time__gte=dtmin).order_by('start_time')
			sleep_ct = sleeps.count()
			for i in range(1, sleep_ct):
				delta = sleeps[i].start_time - sleeps[i - 1].end_time
				if delta.total_seconds() > 3600:
					data = DataReading(user=user, type='awake', value='0', start_time=sleeps[i - 1].end_time, end_time=sleeps[i].start_time)
					data.save()

			# Now go through the 'awake' events making sure they're actual days, and I didn't just take a nap

			joins = []
			prev = None
			for cur in DataReading.objects.filter(user=user, type='awake', start_time__gte=(dtmin - datetime.timedelta(hours=48))).order_by('start_time'):
				if prev is None:
					prev = cur
					continue
				if ((prev.end_time.day == cur.start_time.day) & (prev.end_time.month == cur.start_time.month) & (prev.end_time.year == cur.start_time.year)):
					if len(joins) > 0:
						if joins[-1][1] == prev.pk:
							continue
					joins.append([prev.pk, cur.pk])
				prev = cur

		# This bit counts steps and adds them as DataReadings

		if db_type == 'pebble':
			query = "SELECT date_utc_secs, step_count FROM minute_samples WHERE date_utc_secs>='" + str(int(last_step.start_time.timestamp())) + "';"
		if db_type == 'gadgetbridge':
			query = "select TIMESTAMP, STEPS from PEBBLE_HEALTH_ACTIVITY_SAMPLE WHERE TIMESTAMP>='" + str(int(last_step.start_time.timestamp())) + "';"
		step_count = 0
		try:
			res = c.execute(query)
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
				dp = DataReading.objects.get(user=user, type=type, start_time=dts, end_time=dte)
			except:
				dp = DataReading(user=user, start_time=dts, end_time=dte, type=type, value=steps)
				dp.save()
				step_count = step_count + steps

		if step_count > 0:
			sys.stderr.write(self.style.SUCCESS("Added " + str(step_count) + " steps\n"))

		os.remove(file)
		cache.delete('dashboard')






