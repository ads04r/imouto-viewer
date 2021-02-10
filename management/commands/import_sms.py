from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import DataReading, Event
from io import StringIO
from dateutil.tz import tzlocal
import os, sys, datetime, shutil, sqlite3, pytz, csv, xmltodict, json
from viewer.models import RemoteInteraction

class Command(BaseCommand):
	"""
	Command for importing SMS messages from various (largely pre-historic) formats.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-i", "--input", action="store", dest="input_file", default="", help="The file, containing SMS messages, to be imported.")
		parser.add_argument("-f", "--format", action="store", dest="input_format", default="", help="The type of the file being imported.", choices=['ncc', 'xml', 'msg'])

	def handle(self, *args, **kwargs):

		uploaded_file = os.path.abspath(kwargs['input_file'])

		if ((uploaded_file == '') or (os.path.isdir(uploaded_file))):
			sys.stderr.write(self.style.ERROR("Input file must be specified using the --input switch. See help for more details.\n"))
			sys.exit(1)

		if not(os.path.exists(uploaded_file)):
			sys.stderr.write(self.style.ERROR("File not found: '" + uploaded_file + "'\n"))
			sys.exit(1)

		format = kwargs['input_format']
		if format == '':
			if uploaded_file.lower().endswith('.ncc'):
				format = 'ncc'
			if uploaded_file.lower().endswith('.xml'):
				format = 'xml'
			if uploaded_file.lower().endswith('.msg'):
				format = 'msg'
		if not(format in ['ncc', 'xml', 'msg']):
			sys.stderr.write(self.style.ERROR("File format cannot be identified.\n"))
			sys.exit(1)

		ct = 0

		if format == 'ncc':
			ct = self.import_ncc_file(uploaded_file)
		if format == 'xml':
			ct = self.import_xml_file(uploaded_file)
		if format == 'msg':
			ct = self.import_xml_file(uploaded_file)

		if ct > 0:
			sys.stdout.write(self.style.SUCCESS(str(ct) + " messages successfully imported.\n"))

		cache.delete('dashboard')

	def format_number(self, phone_number):

		ret = phone_number.strip().replace(' ', '')
		if ret.startswith('0'):
			ret = '+44' + ret[1:]
		return ret

	def import_xml_file(self, filename):

		try:
			with open(filename) as fp:
				xml = xmltodict.parse(fp.read())
		except:
			xml = {}

		if 'smses' in xml:
			if 'sms' in xml['smses']:
				return self.import_smsbackuprestore_xml(xml)

		if 'ArrayOfMessage' in xml:
			if 'Message' in xml['ArrayOfMessage']:
				return self.import_windowsphone_xml(xml)

		sys.stderr.write(self.style.ERROR("File format cannot be identified.\n"))
		sys.exit(1)

	def import_windowsphone_xml(self, xml):

		ct = 0
		for msg in xml['ArrayOfMessage']['Message']:
			if not('IsIncoming' in msg):
				continue
			if msg['IsIncoming'] != 'true':
				continue
			if not('Body' in msg):
				continue
			message = msg['Body']
			if message is None:
				continue
			dtt = int(int(msg['LocalTimestamp']) / (10 * 1000 * 1000) - 11644473600)
			dt = datetime.datetime.utcfromtimestamp(dtt).replace(tzinfo=pytz.UTC)
			phone_number = self.format_number(msg['Sender'])
			incoming = True
			try:
				m = RemoteInteraction.objects.get(type='sms', time=dt, address=phone_number, incoming=incoming)
			except:
				m = RemoteInteraction(type='sms', time=dt, address=phone_number, incoming=incoming, title='', message=message)
				print(m.message)
				m.save()
				ct = ct + 1

		for msg in xml['ArrayOfMessage']['Message']:
			if not('IsIncoming' in msg):
				continue
			if msg['IsIncoming'] != 'false':
				continue
			if not('Body' in msg):
				continue
			message = msg['Body']
			if message is None:
				continue
			dtt = int(int(msg['LocalTimestamp']) / (10 * 1000 * 1000) - 11644473600)
			dt = datetime.datetime.utcfromtimestamp(dtt).replace(tzinfo=pytz.UTC)
			phone_number = self.format_number(msg['Recepients']['string'])
			incoming = False
			try:
				m = RemoteInteraction.objects.get(type='sms', time=dt, address=phone_number, incoming=incoming)
			except:
				m = RemoteInteraction(type='sms', time=dt, address=phone_number, incoming=incoming, title='', message=message)
				print(m.message)
				m.save()
				ct = ct + 1

		return ct

	def import_smsbackuprestore_xml(self, xml):

		for msg in xml['smses']['sms']:
			if not('@date' in msg):
				continue
			if not('@address' in msg):
				continue
			if not('@body' in msg):
				continue
			if not('@type' in msg):
				continue
			if not('@protocol' in msg):
				continue
			if msg['@protocol'] != '0':
				continue

			incoming = False
			if msg['@type'] == '1':
				incoming = True
			phone_number = self.format_number(msg['@address'])
			message = msg['@body']
			dtt = int(int(msg['@date']) / 1000)
			dt = datetime.datetime.utcfromtimestamp(dtt).replace(tzinfo=pytz.UTC)
			ct = 0

			try:
				m = RemoteInteraction.objects.get(type='sms', time=dt, address=phone_number, incoming=incoming)
			except:
				m = RemoteInteraction(type='sms', time=dt, address=phone_number, incoming=incoming, title='', message=message)
				print(m.message)
				m.save()
				ct = ct + 1

			return ct

	def import_ncc_file(self, filename):

		data = []
		ct = 0
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

			phone_number = self.format_number(message['1080'])
			try:
				msg = RemoteInteraction.objects.get(type='sms', time=dt, address=phone_number, incoming=True)
			except:
				msg = RemoteInteraction(type='sms', time=dt, address=phone_number, incoming=True, title='', message=message['1033'])
				print(msg.message)
				ct = ct + 1
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
				ct = ct + 1
				msg.save()

		return ct

