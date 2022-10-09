from django.core.management.base import BaseCommand
from django.conf import settings
import os, sys, urllib.request

class Command(BaseCommand):
	"""
	Command for downloading the required Javascript libraries without having to mess about with npm or yarn.
	"""
	def handle(self, *args, **kwargs):

		files = [ ('chart/Chart.js', 'https://cdn.jsdelivr.net/npm/chart.js/dist/Chart.js'),
			  ('chart/Chart.css', 'https://cdn.jsdelivr.net/npm/chart.js/dist/Chart.css'),
			  ('chart/Chart.bundle.js', 'https://cdn.jsdelivr.net/npm/chart.js/dist/Chart.bundle.js'),
			  ('moment/moment.min.js', 'https://raw.githubusercontent.com/ads04r/imouto-viewer/06536ccbaea7885147f300353af0eca4ce2f11a5/static/viewer/script/moment/moment.min.js'),
			  ('leaflet/leaflet-src.js', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet-src.js'),
			  ('leaflet/leaflet.js', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet.js'),
			  ('leaflet/leaflet.css', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet.css'),
			  ('leaflet/images/marker-icon.png', 'https://cdn.jsdelivr.net/npm/leaflet/dist/images/marker-icon.png'),
			  ('leaflet/images/marker-shadow.png', 'https://cdn.jsdelivr.net/npm/leaflet/dist/images/marker-shadow.png'),
			  ('leaflet/images/layers-2x.png', 'https://cdn.jsdelivr.net/npm/leaflet/dist/images/layers-2x.png'),
			  ('leaflet/images/layers.png', 'https://cdn.jsdelivr.net/npm/leaflet/dist/images/layers.png'),
			  ('leaflet/images/marker-icon-2x.png', 'https://cdn.jsdelivr.net/npm/leaflet/dist/images/marker-icon-2x.png'),
			  ('leaflet/leaflet-src.esm.js', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet-src.esm.js'),
			  ('leaflet/leaflet-src.esm.js.map', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet-src.esm.js.map'),
			  ('leaflet/leaflet-src.js.map', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet-src.js.map'),
			  ('leaflet/leaflet.js.map', 'https://cdn.jsdelivr.net/npm/leaflet/dist/leaflet.js.map'),
			  ('fullcalendar/fullcalendar.print.css', 'https://cdn.jsdelivr.net/npm/fullcalendar@2.3.1/dist/fullcalendar.print.css'),
			  ('fullcalendar/fullcalendar.js', 'https://cdn.jsdelivr.net/npm/fullcalendar@2.3.1/dist/fullcalendar.js'),
			  ('fullcalendar/fullcalendar.min.js', 'https://cdn.jsdelivr.net/npm/fullcalendar@2.3.1/dist/fullcalendar.min.js'),
			  ('fullcalendar/fullcalendar.css', 'https://cdn.jsdelivr.net/npm/fullcalendar@2.3.1/dist/fullcalendar.css'),
			  ('fullcalendar/fullcalendar.min.css', 'https://cdn.jsdelivr.net/npm/fullcalendar@2.3.1/dist/fullcalendar.min.css')]

		path = ''
		if hasattr(settings, 'STATIC_ROOT'):
			if settings.STATIC_ROOT != '':
				path = settings.STATIC_ROOT

		if path == '':
			sys.stderr.write(self.style.ERROR("Cannot download files - unknown STATIC_ROOT.\n"))
			sys.exit(1)

		path = os.path.join(path, 'libraries')
		if not(os.path.exists(path)):
			os.makedirs(path)

		for file in files:
			file_path = os.path.join(path, file[0])
			file_dir = os.path.split(file_path)[0]
			if not(os.path.exists(file_dir)):
				os.makedirs(file_dir)
			try:
				urllib.request.urlretrieve(file[1], file_path)
				sys.stderr.write(self.style.SUCCESS(file[1] + " ok\n"))
			except:
				sys.stderr.write(self.style.ERROR(file[1] + " failed\n"))


