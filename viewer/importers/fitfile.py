import datetime, pytz, math
from fit_tool.fit_file import FitFile

from viewer.models import Day, DataReading, ImportedFile

import logging
logger = logging.getLogger(__name__)

def import_fit(parseable_fit_input):
	"""
	Reads data in ANT-FIT format, typically used by Garmin fitness trackers, and generates DataValues based on the information contained within.

	:param parseable_fit_input: A path to an ANT-FIT file.
	"""
	data = []
	earliest_timestamp = None
	latest_timestamp = None
	activity = None
	fit = FitFile.from_file(parseable_fit_input)
	for record in fit.records:
		try:
			name = str(record.message.name)
		except:
			name = ''
		if name == 'sport':
			for recitem in record.message.fields:
				if recitem.get_name() == 'name':
					activity = recitem.get_value()
			continue
		if name != 'record':
			continue
		item = {}
		for recitem in record.message.fields:
			k = recitem.name
			if ((k != 'heart_rate') & (k != 'timestamp') & (k != 'cadence')):
				continue
			v = {}
			v['value'] = recitem.get_value()
			v['units'] = recitem.get_units()
			if ((v['units'] == 'semicircles') & (not(v['value'] is None))):
				v['value'] = float(v['value']) * ( 180 / math.pow(2, 31) )
				v['units'] = 'degrees'
			item[k] = v
		if item['timestamp']['units'] == 'ms':
			item['timestamp'] = {'value': datetime.datetime.utcfromtimestamp(float(item['timestamp']['value']) / 1000), 'units': ''}
		if item['timestamp']['value'].tzinfo is None or item['timestamp']['value'].utcoffset(item['timestamp']['value']) is None:
			item['timestamp']['value'] = pytz.utc.localize(item['timestamp']['value']) # If no timestamp, we assume UTC
		if earliest_timestamp is None:
			earliest_timestamp = item['timestamp']['value']
		if latest_timestamp is None:
			latest_timestamp = item['timestamp']['value']
		if item['timestamp']['value'] < earliest_timestamp:
			earliest_timestamp = item['timestamp']['value']
		if item['timestamp']['value'] > latest_timestamp:
			latest_timestamp = item['timestamp']['value']
		newitem = {}
		newitem['date'] = item['timestamp']['value']
		if 'heart_rate' in item:
			newitem['heart'] = item['heart_rate']['value']
		if 'cadence' in item:
			if item['cadence']['value'] is None:
				item['cadence']['value'] = 0
			if item['cadence']['value'] > 0:
				newitem['cadence'] = item['cadence']['value']
		newitem['length'] = 1
		if len(data) > 0:
			lastitem = data[-1]
			lastitem['length'] = int((newitem['date'] - lastitem['date']).total_seconds())
			data[-1] = lastitem
		data.append(newitem)

	days = []
	for item in data:

		dts = item['date']
		dte = item['date'] + datetime.timedelta(seconds=item['length'])
		dtsd = dts.date()
		dted = dte.date()
		if not(dtsd in days):
			days.append(dtsd)
		if not(dted in days):
			days.append(dted)

		if 'heart' in item:
			if not(item['heart'] is None):
				try:
					event = DataReading.objects.get(start_time=dts, end_time=dte, type='heart-rate')
				except:
					event = DataReading(start_time=dts, end_time=dte, type='heart-rate', value=item['heart'])
					event.save()

		if 'cadence' in item:
			if not(item['cadence'] is None):
				try:
					event = DataReading.objects.get(start_time=dts, end_time=dte, type='cadence')
				except:
					event = DataReading(start_time=dts, end_time=dte, type='cadence', value=item['cadence'])
					event.save()

		if 'speed' in item:
			if not(item['speed'] is None):
				try:
					event = DataReading.objects.get(start_time=dts, end_time=dte, type='speed')
				except:
					event = DataReading(start_time=dts, end_time=dte, type='speed', value=item['speed'])
					event.save()

	for f in ImportedFile.objects.all():
		if f.path == parseable_fit_input:
			f.import_time = pytz.utc.localize(datetime.datetime.utcnow())
			f.earliest_timestamp = earliest_timestamp
			f.latest_timestamp = latest_timestamp
			f.activity = activity
			f.save(update_fields=['activity', 'import_time', 'earliest_timestamp', 'latest_timestamp'])

	for dt in days:
		Day.objects.filter(date=dt).delete()
