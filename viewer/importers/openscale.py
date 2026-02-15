import datetime, pytz, csv
from django.conf import settings

from viewer.models import DataReading

import logging
logger = logging.getLogger(__name__)

def __parse_scale_csv(filepath):

	headers = []
	ret = []
	with open(filepath) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		for row in csv_reader:
			if len(headers) == 0:
				headers = [x.lower() for x in row]
				continue
			i = len(headers)
			j = len(row)
			if i < j:
				j = i
			item = {}
			for i in range(0, j):
				item[headers[i]] = row[i]
			ret.append(item)
	return(ret)

def import_openscale(user, filepath, unit='g'):
	"""
	For users of the Android app OpenScale, this function takes a file exported by the app and
	imports it into the Imouto Viewer database as DataReading objects for weight, fat percentage,
	muscle percentage and water readings.

	:param filepath: The path of the file to be imported.
	:return: A list of lists representing the data that has been imported.
	:rtype: list
	"""
	tz = pytz.timezone(settings.TIME_ZONE)
	ret = []

	data = __parse_scale_csv(filepath)
	for item in data:
		if (('date' in item) & ('time' in item)):
			t = item['time'].split(':')
			if len(t) >= 2:
				ds = item['date'] + ' ' + t[0] + ':' + t[1]
		if 'datetime' in item:
			ds = item['datetime']
		try:
			dt = tz.localize(datetime.datetime.strptime(ds, "%Y-%m-%d %H:%M"))
		except:
			dt = tz.localize(datetime.datetime.strptime(ds, "%d.%m.%Y %H:%M"))

		try:
			weight = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='weight')
		except:
			value = (float(item['weight'])) + 0.5
			if unit == 'kg':
				value = (float(item['weight']) * 1000) + 0.5
			if unit == 'st':
				value = (float(item['weight']) * 6350) + 0.5
			if unit == 'lbs':
				value = (float(item['weight']) * 453.6) + 0.5
			
			if value > 87000:
				weight = DataReading(user=user, start_time=dt, end_time=dt, type='weight', value=int(value))
				ret.append([str(dt), 'weight', str(float(weight.value) / 1000)])
				weight.save()

		if 'fat' in item:
			try:
				fat = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='fat')
			except:
				value = float(item['fat']) + 0.5
				if value > 10:
					fat = DataReading(user=user, start_time=dt, end_time=dt, type='fat', value=int(value))
					ret.append([str(dt), 'fat', str(fat.value) + "%"])
					fat.save()
		if 'body_fat' in item:
			try:
				fat = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='fat')
			except:
				value = float(item['body_fat']) + 0.5
				if value > 10:
					fat = DataReading(user=user, start_time=dt, end_time=dt, type='fat', value=int(value))
					ret.append([str(dt), 'fat', str(fat.value) + "%"])
					fat.save()

		if 'muscle' in item:
			try:
				muscle = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='muscle')
			except:
				value = float(item['muscle']) + 0.5
				if value > 10:
					muscle = DataReading(user=user, start_time=dt, end_time=dt, type='muscle', value=int(value))
					ret.append([str(dt), 'muscle', str(muscle.value) + "%"])
					muscle.save()

		if 'water' in item:
			try:
				water = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='water')
			except:
				value = float(item['water']) + 0.5
				if value > 10:
					water = DataReading(user=user, start_time=dt, end_time=dt, type='water', value=int(value))
					ret.append([str(dt), 'water', str(water.value) + "%"])
					water.save()

		if 'bmi' in item:
			try:
				bmi = DataReading.objects.get(user=user, start_time=dt, end_time=dt, type='bmi')
			except:
				value = float(item['bmi'])
				if value > 10:
					bmi = DataReading(user=user, start_time=dt, end_time=dt, type='bmi', value=int(value + 0.5))
					ret.append([str(dt), 'bmi', str(bmi.value) + "%"])
					bmi.save()

	return ret

