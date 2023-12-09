import django, requests, datetime, pytz, math
from django.conf import settings
from fitparse import FitFile

from viewer.models import Day, DataReading, ImportedFile

def import_fit(parseable_fit_input):
	"""
	Reads data in ANT-FIT format, typically used by Garmin fitness trackers, and generates DataValues based on the information contained within.

	:param parseable_fit_input: A path to an ANT-FIT file.
	"""
	data = []
	fit = FitFile(parseable_fit_input)
	for record in fit.get_messages('record'):
		item = {}
		for recitem in record:
			k = recitem.name
			if ((k != 'heart_rate') & (k != 'timestamp') & (k != 'cadence')):
				continue
			v = {}
			v['value'] = recitem.value
			v['units'] = recitem.units
			if ((v['units'] == 'semicircles') & (not(v['value'] is None))):
				v['value'] = float(v['value']) * ( 180 / math.pow(2, 31) )
				v['units'] = 'degrees'
			item[k] = v
		if item['timestamp']['value'].tzinfo is None or item['timestamp']['value'].utcoffset(item['timestamp']['value']) is None:
			item['timestamp']['value'] = pytz.utc.localize(item['timestamp']['value']) # If no timestamp, we assume UTC
		newitem = {}
		newitem['date'] = item['timestamp']['value']
		if 'heart_rate' in item:
			newitem['heart'] = item['heart_rate']['value']
		if 'cadence' in item:
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
			f.save()

	for dt in days:
		Day.objects.filter(date=dt).delete()

