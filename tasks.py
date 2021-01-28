from background_task import background
from .models import *
from .functions import *
from xml.dom import minidom
from tzlocal import get_localzone
import datetime, pytz, os

@background(schedule=0, queue='reports')
def generate_report(title, dss, dse, type='year', style='default'):
	""" A background task for generating LifeReport objects"""

	dts = datetime.datetime.strptime(dss, "%Y-%m-%d %H:%M:%S %Z")
	dte = datetime.datetime.strptime(dse, "%Y-%m-%d %H:%M:%S %Z")

	tz = get_localzone()
	now = pytz.UTC.localize(datetime.datetime.utcnow())
	report = LifeReport(label=title, type=type, style=style, modified_date=now)
	report.save()
	photos = 0
	for event in Event.objects.filter(start_time__lte=dte, end_time__gte=dts).order_by('start_time'):
		if event.location:
			report.locations.add(event.location)
		if event.type == 'life_event':
			report.events.add(event)
		if event.description != '':
			report.events.add(event)
		if event.photos().count() > 5:
			report.events.add(event)
		for person in event.people.all():
			report.people.add(person)
		photos = photos + event.photos().count()
	report.addproperty(key='Photos Taken', value=photos)
	countries = report.countries().count()
	if countries > 1:
		prop = report.addproperty(key='Countries Visited', value=(countries - 1))
		prop.icon = 'globe'
		prop.save()

	generate_report_pdf(report.id, style)

	return report

@background(schedule=0, queue='reports')
def generate_report_pdf(reportid, style):
	""" A background task for creating a PDF report based on a LifeReport object """

	report = LifeReport.objects.get(id=reportid)

	return report

