from viewer.models import DataReading

import logging
logger = logging.getLogger(__name__)

def import_data(data):
	"""
	Import generic sensor data into Imouto's database.

	:param data: A list of dicts. The dicts must all contain the keys start_time, end_time, type and value.
	:return: A three-item tuple representing the number of new records inserter, the number of records updated, and the number of records that could not be imported, in that order.
	:rtype: tuple
	"""
	done = 0
	updated = 0
	inserted = 0
	for item in data:
		done = done + 1
		try:
			e = DataReading.objects.get(start_time=item['start_time'], end_time=item['end_time'], type=item['type'])
			e.value = item['value']
			e.save()
			updated = updated + 1
		except:
			e = DataReading(start_time=item['start_time'], end_time=item['end_time'], type=item['type'], value=item['value'])
			e.save()
			inserted = inserted + 1

	return (inserted, updated, (len(data) - done))
