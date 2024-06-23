import django, datetime, pytz, csv
from django.conf import settings
from django.db.models import Q
from django.core.files import File
from django.core.cache import cache

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
				headers = row
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

def import_openscale(filepath):
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
		ds = item['dateTime']
		try:
			dt = tz.localize(datetime.datetime.strptime(ds, "%Y-%m-%d %H:%M"))
		except:
			dt = tz.localize(datetime.datetime.strptime(ds, "%d.%m.%Y %H:%M"))

		try:
			weight = DataReading.objects.get(start_time=dt, end_time=dt, type='weight')
		except:
			value = (float(item['weight']) * 1000) + 0.5
			if value > 87000:
				weight = DataReading(start_time=dt, end_time=dt, type='weight', value=int(value))
				ret.append([str(dt), 'weight', str(float(weight.value) / 1000)])
				weight.save()

		try:
			fat = DataReading.objects.get(start_time=dt, end_time=dt, type='fat')
		except:
			value = float(item['fat']) + 0.5
			if value > 10:
				fat = DataReading(start_time=dt, end_time=dt, type='fat', value=int(value))
				ret.append([str(dt), 'fat', str(fat.value) + "%"])
				fat.save()

		try:
			muscle = DataReading.objects.get(start_time=dt, end_time=dt, type='muscle')
		except:
			value = float(item['muscle']) + 0.5
			if value > 10:
				muscle = DataReading(start_time=dt, end_time=dt, type='muscle', value=int(value))
				ret.append([str(dt), 'muscle', str(muscle.value) + "%"])
				muscle.save()

		try:
			water = DataReading.objects.get(start_time=dt, end_time=dt, type='water')
		except:
			value = float(item['water']) + 0.5
			if value > 10:
				water = DataReading(start_time=dt, end_time=dt, type='water', value=int(value))
				ret.append([str(dt), 'water', str(water.value) + "%"])
				water.save()
	return ret

