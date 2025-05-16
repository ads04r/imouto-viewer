import datetime, pytz, os, re
from viewer.models import RemoteInteraction, Person
from dateutil import parser
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

def import_pidgin_log_file(filename, uid, name):
	"""
	Imports a file from IM software Pidgin into Imouto as RemoteInteraction objects, so they show up
	and behave like SMS and other text messages.

	:param filename: The file to import.
	:param uid: The Imouto uid of the other person in the conversation.
	:param name: The name of the other person in the conversation, as it appears in the log file.
	:return: The number of new messages imported.
	:rtype: int
	"""
	try:
		person = Person.objects.get(uid=uid)
	except:
		return 0 # The uid doesn't exist, so we do nothing.
	if not os.path.exists(filename):
		return 0 # The file doesn't exist, so do nothing.
	dt = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	ret = 0
	tz = pytz.timezone(settings.TIME_ZONE)
	with open(filename, 'r') as fp:
		for row in fp.readlines():
			head = re.search(r'^Conversation with (.+) at (.+) on (.+)$', row)
			if not head is None:
				dt = parser.parse(head.group(2)).astimezone(tz)
				continue
			item = re.search(r'\(([^\)]+)\)([^:]+):(.+)', row.rstrip())
			if item is None:
				continue
			t = re.search(r'^(\d+):(\d+):(\d+)$', item.group(1))
			if t is None:
				last_dt = dt
				try:
					dt = parser.parse(item.group(1)).astimezone(tz)
				except:
					dt = last_dt
				if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None: # ie if the datetime is naive
					dt = last_dt.tzinfo.localize(dt)
			else:
				dt = datetime.datetime(dt.year, dt.month, dt.day, int(t.group(1)), int(t.group(2)), int(t.group(3)), tzinfo=dt.tzinfo)
			cmp = item.group(2).strip().lower()
			incoming = (cmp == name.strip().lower())
			body = item.group(3)
			try:
				msg = RemoteInteraction.objects.get(type='im', time=dt, address='', incoming=incoming, title='', contact=person, message=body)
			except:
				msg = RemoteInteraction(type='im', time=dt, address='', incoming=incoming, title='', contact=person, message=body)
				ret = ret + 1
				msg.save()
	return ret
