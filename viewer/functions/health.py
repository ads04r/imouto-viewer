import datetime, time, pytz, sys, os
from viewer.models import DataReading, Event, Day
from viewer.health import parse_sleep
from django.db.models import F, ExpressionWrapper, DurationField
from django.core.cache import cache
from django.conf import settings

from viewer.models import create_or_get_day

import logging
logger = logging.getLogger(__name__)

def get_weight_history(days):
	"""
	Returns the stored weight values for the last [n] days.

	:param days: The number of days worth of history to return.
	:return: A list of two-value lists consisting of a time offset and a weight in kg.
	:rtype: list
	"""
	dte = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
	dts = dte - datetime.timedelta(days=days)
	data = DataReading.objects.filter(start_time__gte=dts, type='weight').order_by('start_time')
	ret = []
	last = 0
	if data.count() > 0:
		last = int(time.mktime(data[0].start_time.timetuple()))
	for item in data:
		dt = int(time.mktime(item.start_time.timetuple()))
		ret.append([(dt - last), float(item.value) / 1000])
	return ret

def get_heart_history(days):
	"""
	Returns the stored heart rate values for the last [n] days.

	:param days: The number of days worth of history to return.
	:return: A list of two-value lists consisting of a time offset and a heart rate in beats per minute.
	:rtype: list
	"""
	dte = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
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

def get_weight_graph(dts, dte):
	"""
	Returns the stored weight values for a time range, for the purpose of drawing a graph.

	:param dts: A Python datetime object representing the start time of the range being queried.
	:param dte: A Python datetime object representing the end time of the range.
	:return: A list of two-value lists consisting of graph co-ordinates, with time on the x-axis and weight in kg on the y-axis.
	:rtype: list
	"""
	key = 'weightgraph_' + dts.strftime("%Y%m%d%H%M%S") + dte.strftime("%Y%m%d%H%M%S")
	ret = cache.get(key)
	if not(ret is None):
		return ret

	ret = []
	for item in DataReading.objects.filter(start_time__lt=dte, end_time__gte=dts, type='weight').order_by('start_time'):
		dtx = item.start_time.astimezone(pytz.utc)
		item = {'x': dtx.strftime("%Y-%m-%dT%H:%M:%S"), 'y': float(item.value) / 1000}
		ret.append(item)

	cache.set(key, ret, timeout=86400)

	return(ret)

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

	dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0))
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
	Returns the stored wake history for the last [n] days.

	:param days: The number of days worth of history to return.
	:return: A list containing two sub-lists, one for wake-up times and one for bed times. Times are in seconds since midnight, because it makes graph-drawing easier.
	:rtype: list
	"""
	dte = datetime.datetime.utcnow().date()
	dts = dte - datetime.timedelta(days=days)
	ret = [[], []]

	dt = dts
	while dt < dte:
		day = create_or_get_day(dt)
		dt = dt + datetime.timedelta(days=1)
		tts = day.wake_time
		tte = day.bed_time
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

