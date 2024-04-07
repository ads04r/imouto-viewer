from django.conf import settings
import datetime, pytz, dateparser, re

from viewer.models import RemoteInteraction

def import_pidgin_log(filename, im_type, outgoing_handle, replace_target=''):
	"""
	Imports a Pidgin (libpurple) log file into Imouto as RemoteInteractions.
	"""
	#minmsg = RemoteInteraction.objects.filter(type='im').order_by('-time')[0]
	#mindt = minmsg.time
	#minds = mindt.strftime("%-d-%b-%Y")

	data = []
	names = []
	tz = pytz.timezone(settings.TIME_ZONE)
	with open(filename, 'r') as fp:
		for l in fp.readlines():
			m = re.match(r'\(([^a-zA-Z]+)\) ([^:]+): (.*)', l.strip())
			if m:
				ll = m.groups()
				if len(ll) == 3:
					item = []
					handle = ll[1]
					item.append(tz.localize(dateparser.parse(ll[0])))
					item.append(handle)
					item.append(ll[2])
					if not(handle in names):
						names.append(handle)
					data.append(item)

	if not(outgoing_handle in names):
		names.append(outgoing_handle)
	if len(names) > 2:
		return []

	ret = []
	recipient = ''
	for name in names:
		if name != outgoing_handle:
			recipient = name
	for item in data:
		item.append(im_type)
		if item[1] == outgoing_handle:
			item.append(False)
			item[1] = ''
		else:
			item.append(True)
			if len(replace_target) > 0:
				item[1] = replace_target
		if item[1] == '':
			if len(replace_target) == 0:
				item[1] = recipient
			else:
				item[1] = replace_target
		try:
			ri = RemoteInteraction.objects.get(type=item[3], time=item[0], incoming=item[4], address=item[1])
		except:
			ri = RemoteInteraction(type=item[3], time=item[0], incoming=item[4], address=item[1], message=item[2])
			ri.save()
		ret.append(ri)

	return ret

#class RemoteInteraction(models.Model):
#        type = models.SlugField(max_length=32)
#        time = models.DateTimeField()
#        address = models.CharField(max_length=128)
#        incoming = models.BooleanField()
#        title = models.CharField(max_length=255, default='', blank=True)
#        message = models.TextField(default='', blank=True)


# [[datetime.datetime(2024, 6, 4, 17, 6, 12, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'Turns out Ive had my phone tethering on since Thursday. So everywhere I go, a network called "Fuck Virgin Media" has been following me.', 'im_telegram', True], 
#  [datetime.datetime(2024, 6, 4, 17, 6, 48, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', "Haha that's kind of funny 😂", 'im_telegram'],
#  [datetime.datetime(2024, 6, 4, 18, 55, 39, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', "I guess you can always tell when I order food when you're not here now 😂", 'im_telegram'],
#  [datetime.datetime(2024, 6, 4, 19, 0, 40, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'I could anyway! If the doorbell rings in the evening who else is it going to be? :P', 'im_telegram', True],
#  [datetime.datetime(2024, 6, 4, 19, 2, 5, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', 'Could have been my secret boyfriend 😂', 'im_telegram'],
#  [datetime.datetime(2024, 6, 4, 19, 9, 22, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', "Presumably he doesn't ring the doorbell 😜", 'im_telegram', True],
#  [datetime.datetime(2024, 6, 4, 19, 9, 41, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', 'Not anymore 😂', 'im_telegram'],
#  [datetime.datetime(2024, 6, 4, 19, 10, 11, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', "Hope you're OK. Has there been any singing yet? X", 'im_telegram'],
#  [datetime.datetime(2024, 6, 4, 19, 17, 51, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'Yes a few. Its early yet, Im just the DJ at the minute. Sadly one song jas been a 12-minute Oasis song 😞', 'im_telegram', True],
#  [datetime.datetime(2024, 6, 4, 19, 18, 9, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', 'Oh flipping heck!', 'im_telegram'], [datetime.datetime(2024, 6, 4, 19, 50, 42, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', 'In not very interesting news...the Kodi box now does a thing where it plays the next episode of the thing you are watching straight after the last one like Netflix does. It means you can never go to bed!!', 'im_telegram'], [datetime.datetime(2024, 6, 4, 20, 13, 37, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'Oh, I didnt know it did that!', 'im_telegram', True], [datetime.datetime(2024, 6, 4, 20, 14, 2, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', "I'm pretty sure it just started it today. It certainly didn't do it before", 'im_telegram'], [datetime.datetime(2024, 6, 4, 20, 17, 40, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'An ugly male rugby player is singing Dancing Queen very badly.', 'im_telegram', True], [datetime.datetime(2024, 6, 4, 20, 17, 55, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', 'Is it Russ? 😂', 'im_telegram'], [datetime.datetime(2024, 6, 4, 20, 22, 11, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'Flarpy', 'No. Russ doesnt have the range of a blue whale.', 'im_telegram', True], [datetime.datetime(2024, 6, 4, 20, 25, 16, tzinfo=<DstTzInfo 'Europe/London' BST+1:00:00 DST>), 'wife', '😂', 'im_telegram']]
