from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from viewer.models import DataReading, Event, EventWorkoutCategory, TransitMethod
from viewer.tasks.datacrunching import regenerate_similar_events
from viewer.functions.geo import get_area_name
from viewer.functions.location_manager import getgeoline, get_location_manager_report_queue
from xml.dom import minidom
import os, sys, datetime, pytz, json

class Command(BaseCommand):
	"""
	Command for generating walk events from previously imported activity data.
	"""
	def handle(self, *args, **kwargs):

		for user in User.objects.all():

			try:
				dt = Event.objects.filter(user=user, type='journey', caption__icontains='walk').order_by('-start_time')[0].start_time
			except:
				continue
			for walk in DataReading.objects.filter(user=user, type='pebble-app-activity', value='5', start_time__gte=dt):
				if Event.objects.filter(user=user, type='journey', start_time__lte=walk.end_time, end_time__gte=walk.start_time).count() > 0:
					continue
				if Event.objects.filter(user=user, type='journey', start_time__lte=walk.start_time, end_time__gte=walk.end_time).count() > 0:
					continue

				try:
					transit = TransitMethod.objects.get(user=user, label__iexact='walking')
				except:
					transit = None

				event = Event(user=user, type='journey', transit_method=transit, caption='Walk', start_time=walk.start_time, end_time=walk.end_time)

				try:
					data = json.loads(getgeoline(user, event.start_time, event.end_time))
				except json.decoder.JSONDecodeError:
					data = {}
				try:
					walking = EventWorkoutCategory.objects.get(user=user, pk='walking')
				except:
					walking = None
				if walking is None:
					try:
						walking = EventWorkoutCategory.objects.get(user=user, pk='walk')
					except:
						walking = None
				if walking is None:
					sys.exit(0)

				if 'geometry' in data:
					if 'coordinates' in data['geometry']:
						if len(data['geometry']['coordinates']) > 0:
							event.geo = json.dumps(data)
					if 'geometries' in data['geometry']:
						if len(data['geometry']['geometries']) > 0:
							event.geo = json.dumps(data)
				location_text = ''
				if 'bbox' in data:
					location_text = get_area_name(data['bbox'][1], data['bbox'][0], data['bbox'][3], data['bbox'][2])
					if location_text != '':
						if 'properties' in data:
							if 'distance' in data['properties']:
								location_text = str(float(int(data['properties']['distance'] * 10)) / 10) + 'km walk in ' + location_text
						else:
							location_text = 'Walk in ' + location_text
				if location_text == '':
					if 'properties' in data:
						if 'distance' in data['properties']:
							location_text = str(float(int(data['properties']['distance'] * 10)) / 10) + 'km walk'
				if location_text.startswith('0.0km walk'):
					location_text = ''

				if location_text != '':
					cache.delete('dashboard')
					event.caption = location_text
					event.save()
					sys.stderr.write(self.style.SUCCESS("Creating event: " + str(user.username) + "/" + str(event.pk) + " " + event.caption + "\n"))
					event.workout_categories.add(walking)
					regenerate_similar_events(user.pk, event.id)
					h = event.health()
