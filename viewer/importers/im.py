from django.conf import settings
import datetime, pytz, dateparser, re

from viewer.models import RemoteInteraction

def import_pidgin_log(filename):
	"""
	Imports a Pidgin (libpurple) log file into Imouto as RemoteInteractions.
	"""
	#minmsg = RemoteInteraction.objects.filter(type='im').order_by('-time')[0]
	#mindt = minmsg.time
	#minds = mindt.strftime("%-d-%b-%Y")

	ret = []
	tz = pytz.timezone(settings.TIME_ZONE)
	with open(filename, 'r') as fp:
		for l in fp.readlines():
			m = re.match(r'\(([^a-zA-Z]+)\) ([^:]+): (.*)', l.strip())
			if m:
				ll = m.groups()
				if len(ll) == 3:
					item = []
					item.append(tz.localize(dateparser.parse(ll[0])))
					item.append(ll[1])
					item.append(ll[2])
					ret.append(item)

	for item in ret:
		print(item)
