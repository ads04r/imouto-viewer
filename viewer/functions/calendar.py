from viewer.models import CalendarAppointment

import logging
logger = logging.getLogger(__name__)

def event_label(user, start_time, end_time):
	"""
	Returns a human readable string based on any known calendar events that are active during the specified time window.

	:param start_time: A Python datetime, the start of the period to be queried.
	:param end_time: A Python datetime, the end of the period to be queried.
	:return: A string, typically the title of a calendar event, empty string if none found.
	:rtype: str

	"""
	apts = CalendarAppointment.objects.filter(user=user, start_time__lte=end_time, end_time__gte=start_time)
	if apts.count() == 1:
		return apts.first().caption
	apts = CalendarAppointment.objects.filter(user=user, start_time__lte=start_time, end_time__gte=end_time)
	if apts.count() == 1:
		return apts.first().caption
	return ""
