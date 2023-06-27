import datetime, time, pytz, sys, os
from viewer.models import DataReading, Event
from viewer.health import parse_sleep
from django.db.models import F, ExpressionWrapper, DurationField
from django.core.cache import cache
from django.conf import settings

def get_heart_history(days):
	"""
	Returns the stored heart rate values for the last [n] days.

	:param days: The number of days worth of history to return.
	:return: A list of two-value lists consisting of a time offset and a heart rate in beats per minute.
	:rtype: list
	"""
	dte = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
	dts = dte - datetime.timedelta(days=days)
	data = DataReading.objects.filter(start_time__gte=dts, type='heart-rate').order_by('start_time')
	ret = []
	last = 0
	if data.count() > 0:
		last = int(time.mktime(data[0].start_time.timetuple()))
	for item in data:
		dt = int(time.mktime(item.start_time.timetuple()))
		ret.append([(dt - last), item.value])
	return ret

def get_heart_graph(dt):
	"""
	Returns the stored heart rate values for an entire day, for the purpose of drawing a graph.

	:param dt: A Python date object representing the day being queried.
	:return: A list of two-value lists consisting of graph co-ordinates, with time on the x-axis and heart rate in bpm on the y-axis.
	:rtype: list
	"""
	key = 'heartgraph_' + dt.strftime("%Y%m%d")
	ret = cache.get(key)
	if not(ret is None):
		return ret

	dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = dts + datetime.timedelta(days=1)
	last = None
	values = {}
	for item in DataReading.objects.filter(start_time__lt=dte, end_time__gte=dts, type='heart-rate').order_by('start_time'):
		dtx = int((item.start_time - dts).total_seconds() / 60)
		if dtx in values:
			if item.value < values[dtx]:
				continue
		values[dtx] = item.value
	ret = []
	for x in range(0, 1440):
		dtx = dts + datetime.timedelta(minutes=x)
		if x in values:
			y = values[x]
			if not(last is None):
				td = (dtx - last).total_seconds()
				if td > 600:
					item = {'x': (last + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
					ret.append(item)
					item = {'x': (dtx - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
					ret.append(item)
			item = {'x': dtx.strftime("%Y-%m-%dT%H:%M:%S"), 'y': y}
			last = dtx
			ret.append(item)

	cache.set(key, ret, timeout=86400)

	return(ret)

def get_sleep_history(days):
	"""
	Returns the stored wake hitsory for the last [n] days.

	:param days: The number of days worth of history to return.
	:return: A list containing two sub-lists, one for wake-up times and one for bed times.
	:rtype: list
	"""
	dte = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
	dts = dte - datetime.timedelta(days=days)
	data = DataReading.objects.filter(start_time__gte=dts, type='awake').order_by('start_time')
	ret = [[], []]
	for item in data:
		tts = item.start_time.astimezone(pytz.timezone(settings.TIME_ZONE))
		tte = item.end_time.astimezone(pytz.timezone(settings.TIME_ZONE))
		wake_secs = (tts - tts.replace(hour=0, minute=0, second=0)).total_seconds()
		sleep_secs = (tte - tts).total_seconds() + wake_secs
		if len(ret[0]) == 0:
			ret[0].append(wake_secs)
			ret[1].append(sleep_secs)
			continue
		if (ret[1][-1] + 3600) < wake_secs:
			ret[1][-1] = sleep_secs
		else:
			ret[0].append(wake_secs)
			ret[1].append(sleep_secs)
	return ret

