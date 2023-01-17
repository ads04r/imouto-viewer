import datetime, time, pytz, sys, os
from viewer.models import *
from django.db.models import F, ExpressionWrapper, DurationField
from django.core.cache import cache
from django.conf import settings

def max_heart_rate(self, at_time=None):
	if at_time is None:
		dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
	else:
		dt = at_time
	age = int(((dt - datetime.datetime(settings.USER_DATE_OF_BIRTH.year, settings.USER_DATE_OF_BIRTH.month, settings.USER_DATE_OF_BIRTH.day, 0, 0, 0, tzinfo=dt.tzinfo)).days) / 365.25)
	return (220 - age)

def get_heart_history(days):

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

def get_heart_information(dt, graph=True):

	dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = dts + datetime.timedelta(days=1)
	dts_now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
	dts_prev = dts - datetime.timedelta(days=1)
	dts_next = dts + datetime.timedelta(days=1)

	data = {'date': dts.strftime("%a %-d %b %Y"), 'heart': {}}

	data['prev'] = dts_prev.strftime("%Y%m%d")
	if dts_next < dts_now:
		data['next'] = dts_next.strftime("%Y%m%d")

	max_rate = 220 - int(((dts_now.date() - settings.USER_DATE_OF_BIRTH).days) / 365.25)
	zone_1 = int(float(max_rate) * 0.5)
	zone_2 = int(float(max_rate) * 0.7)

	data['heart']['abs_max_rate'] = max_rate

	max = 0
	zone = [0, 0, 0]
	for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte):
		if event.cached_health:
			health = event.health()
			if 'heartmax' in health:
				if health['heartmax'] > max:
					max = health['heartmax']
			if 'heartzonetime' in health:
				zone[0] = zone[0] + health['heartzonetime'][0]
				zone[1] = zone[1] + health['heartzonetime'][1]
				zone[2] = zone[2] + health['heartzonetime'][2]
	if max > 0:
		total_heart_time = zone[0] + zone[1] + zone[2]
		if ((total_heart_time > 0) & (total_heart_time < 86400)):
			zone[0] = zone[0] + (86400 - total_heart_time)
		data['heart']['day_max_rate'] = max
		data['heart']['heartzonetime'] = zone
		if graph:
			data['heart']['graph'] = get_heart_graph(dt)
	else:
		del data['heart']

	return data

def get_sleep_history(days):

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

def get_sleep_information(dt):

	dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dte = datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=pytz.timezone(settings.TIME_ZONE))
	dts_now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
	dts_prev = dts - datetime.timedelta(days=1)
	dts_next = dts + datetime.timedelta(days=1)

	expression = F('end_time') - F('start_time')
	wrapped_expression = ExpressionWrapper(expression, DurationField())

	data = {'date': dts.strftime("%a %-d %b %Y")}
	awake_set = DataReading.objects.filter(type='awake', start_time__gte=dts).annotate(length=wrapped_expression).filter(length__gte=datetime.timedelta(minutes=60)).order_by('start_time')
	event_count = awake_set.count()
	if event_count >= 1:
		awake = awake_set[0]
		data['wake_up'] = awake.start_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
		data['bedtime'] = awake.end_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
		data['wake_up_local'] = awake.start_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lstrip("0").lower()
		data['bedtime_local'] = awake.end_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lstrip("0").lower()
		data['length'] = awake.length.total_seconds()
		try:
			tomorrow = DataReading.objects.filter(type='awake', start_time__gt=dte).order_by('start_time')[0].start_time
			data['tomorrow'] = tomorrow.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
		except IndexError:
			tomorrow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
		if event_count >= 2:
			sleep_data = []
			for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=awake.start_time, end_time__lte=tomorrow).order_by('start_time'):
				sleep_data.append(sleep_info)
			if len(sleep_data) > 0:
				data['sleep'] = parse_sleep(sleep_data)
		else:
			sleep_data = []
			for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=awake.start_time).order_by('start_time'):
				sleep_data.append(sleep_info)
			if len(sleep_data) > 0:
				data['sleep'] = parse_sleep(sleep_data)
	data['prev'] = dts_prev.strftime("%Y%m%d")
	if dts_next < dts_now:
		data['next'] = dts_next.strftime("%Y%m%d")

	return data
