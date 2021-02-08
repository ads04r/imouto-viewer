from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import DataReading, Event
from io import StringIO
from dateutil.tz import tzlocal
import os, sys, datetime, shutil, sqlite3, pytz, csv
from viewer.models import RemoteInteraction

class Command(BaseCommand):
	"""
	Command for importing SMS messages from a Nokia mobile phone
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="An NCC file, exported by Nokia PC Suite / Content Copier")

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])

		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)

		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			sys.exit(1)

		self.import_ncc_file(uploaded_file)
		cache.delete('dashboard')

	def import_ncc_file(self, filename):

		data = []
		fp = open(filename, 'rb')
		csvb = fp.read()
		fp.close()
		csvs = csvb.decode('utf16')
		f = StringIO(csvs)
		r = csv.reader(f, delimiter='\t', quotechar='"')
		for row in r:
			item = {}
			i = 0
			while i <= (len(row) - 1):
				key = row[i]
				value = row[(i + 1)]
				item[key] = value
				i = i + 2
			data.append(item)

		for message in data:
			if not('1020' in message):
				continue
			if message['1020'] != 'PIT_MESSAGE_INBOX':
				continue
			dt = datetime.datetime.strptime(message['1041'], '%Y-%m-%dT%H:%M').replace(tzinfo=tzlocal())

			try:
				msg = RemoteInteraction.objects.get(type='sms', time=dt, address=message['1080'], incoming=True)
			except:
				msg = RemoteInteraction(type='sms', time=dt, address=message['1080'], incoming=True, title='testing', message=message['1033'])
				print(msg.message)
				msg.save()

		for message in data:
			if not('1021' in message):
				continue
			if not('1041' in message):
				continue
			if not('1081' in message):
				continue
			if message['1021'] != 'PIT_MESSAGE_OUTBOX':
				continue
			dt = datetime.datetime.strptime(message['1041'], '%Y-%m-%dT%H:%M').replace(tzinfo=tzlocal())
			try:
				msg = RemoteInteraction.objects.get(type='sms', time=dt, address=message['1081'], incoming=True)
			except:
				msg = RemoteInteraction(type='sms', time=dt, address=message['1081'], incoming=True, title='', message=message['1033'])
				print(msg.message)
				msg.save()

