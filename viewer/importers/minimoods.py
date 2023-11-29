import django
from django.conf import settings
from dateutil import parser
import os, csv, datetime

from viewer.importers.core import import_data

def import_mood_file(path):
	"""
	Import Mini-Moods data into Imouto's database. Mini-Moods is an Android app available from F-Droid.

	:param path: The path of the file to import. Should be a CSV file exported from Mini-Moods.
	:return: A three-item tuple representing the number of new records inserted, the number of records updated, and the number of records that could not be imported, in that order.
	:rtype: tuple
	"""
	uploaded_file = os.path.abspath(path)

	data = []
	with open(uploaded_file, newline='\n') as csvfile:
		r = csv.reader(csvfile, delimiter=',', quotechar='"')
		for row in r:
			if len(row) < 2:
				continue
			dts = parser.parse(row[0])
			dte = dts + datetime.timedelta(seconds=86399)
			v = 6 - int(row[1])
			if v > 5:
				continue
			if v < 1:
				continue
			data.append({'start_time': dts, 'end_time': dte, 'type': 'mood', 'value': v})

	if len(data) == 0:
		return (0, 0, 0)
	return import_data(data)
