from viewer.models import CalendarAppointment

def event_label(start_time, end_time):

	apts = CalendarAppointment.objects.filter(start_time__lte=end_time, end_time__gte=start_time)
	if apts.count() == 1:
		return apts.first().caption
	apts = CalendarAppointment.objects.filter(start_time__lte=start_time, end_time__gte=end_time)
	if apts.count() == 1:
		return apts.first().caption
	return ""
