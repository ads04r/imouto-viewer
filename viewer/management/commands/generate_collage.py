from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from viewer.models import Event, Photo
import os, sys, datetime, shutil, sqlite3, pytz, json, random

class Command(BaseCommand):
	"""
	Command for generating photo collages for significant events.
	"""
	def add_arguments(self, parser):

		parser.add_argument('-e', '--event', action='store', dest='event', default='', type=str, help='Optional, the ID of the event for which we want to generate a collage.')

	def handle(self, *args, **kwargs):

		dt = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=7)
		id = kwargs['event']
		event = None
		if id != '':
			try:
				event = Event.objects.get(id=id)
			except ObjectDoesNotExist:
				event = None

		if event is None:
			events = []
			for e in Event.objects.filter(type='life_event', end_time__lte=dt).order_by('?'):
				for ee in e.subevents().filter(collage=None):
					if ee.photos().count() < 3:
						continue
					events.append(ee)
			random.shuffle(events)
			for e in events:
				if e.photos().count() < 3:
					continue
				event = e
				break

		if event is None:
			for e in Event.objects.filter(collage=None, type='event', end_time__lte=dt).order_by('?'):
				if e.photos().count() < 3:
					continue
				event = e
				break

		if event is None:
			for e in Event.objects.filter(collage=None, type='photos', end_time__lte=dt).order_by('?'):
				if e.photos().count() < 3:
					continue
				event = e
				break

		if event is None:
			for e in Event.objects.filter(collage=None, end_time__lte=dt).order_by('?'):
				if e.photos().count() < 3:
					continue
				event = e
				break

		if event is None:
			sys.stderr.write('Event not found, or no events available.\n')
			sys.exit(1)

		sys.stderr.write(str(event.id) + ': ' + str(event) + '... ')
		event.collage = None
		event.save()
		im = event.photo_collage()
		sys.stderr.write('done\n')
