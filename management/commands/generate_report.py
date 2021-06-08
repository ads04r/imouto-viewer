from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import *
from viewer.tasks import generate_report, generate_report_pdf
import os, sys, datetime, shutil, sqlite3, pytz, json, urllib.request

class Command(BaseCommand):
	"""
	Command for importing weather data from OpenWeatherMap. This functionality needs the OPENWEATHERMAP_API_KEY setting to be set.
	"""
	def add_arguments(self, parser):

		choices = []
		first_event = Event.objects.all().order_by('start_time')[0].start_time.year
		last_event = Event.objects.all().order_by('-start_time')[0].start_time.year
		last_year = datetime.datetime.now().year - 1
		if last_year < last_event:
			last_event = last_year
		for i in range(first_event, (last_event + 1)):
			choices.append(str(i))
		parser.add_argument('year', metavar='year', type=str, nargs='+', choices=choices, help='The year for which to create a report.')
		parser.add_argument("-t", "--title", action="store", dest="title", default="", help="The human-readable title of the year report. Defaults to the year as a number.")

	def handle(self, *args, **kwargs):

		years = kwargs['year']
		title = kwargs['title']
		if len(years) > 1:
			title = ''

		for year in years:
			report_title = title
			try:
				reports = LifeReport.objects.filter(reportevents__event__start_time__year=year, reportevents__event__end_time__year=year).distinct()
				report = None
				if reports.count() == 1:
					report = reports[0]
			except:
				report = None
			if report_title == '':
				if report is None:
					report_title = str(year)
				else:
					report_title = report.label

			properties = []
			if not(report is None):
				for prop in report.properties.all():
					properties.append([prop.key, prop.value, prop.category, prop.icon, prop.description])
				if report.pdf:
					report.pdf.delete()
				report.delete()
			sys.stdout.write(self.style.SUCCESS("Generating " + report_title + "\n"))

			report = generate_report.now(report_title, str(year) + "-01-01 00:00:00 +0000", str(year) + "-12-31 23:59:59 +0000", pdf=False)
			sys.stdout.write(self.style.SUCCESS("* Adding properties\n"))
			for prop in properties:
				try:
					item = LifeReportProperties.objects.get(category=prop[2], key=prop[0], value=prop[1], report=report)
				except:
					item = None
				if not(item is None):
					continue
				item = report.addproperty(prop[0], prop[1], prop[2])
				item.icon = prop[3]
				item.description = prop[4]
				item.save()
				sys.stdout.write("   " + prop[0] + "\n")

			sys.stdout.write(self.style.SUCCESS("* Generating PDF\n"))
			generate_report_pdf.now(report.pk, 'default')
