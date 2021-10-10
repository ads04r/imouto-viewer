from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from viewer.models import Event
from viewer.tasks import generate_photo_collages
from random import shuffle

class Command(BaseCommand):
	"""
	Command for finding events that will be included in life reports, and calling the collage generation script for these events.
	"""
	def handle(self, *args, **kwargs):

		min_photos = 1

		events = []
		for le in Event.objects.filter(type='life_event'):
			for e in le.subevents():
				if len(e.photos()) < min_photos:
					continue
				if le.photo_collages.count() > 0:
					continue
				events.append(e.id)
		for e in Event.objects.filter(type='event'):
			if len(e.photos()) < min_photos:
				continue
			if e.photo_collages.count() > 0:
				continue
			events.append(e.id)

		shuffle(events)

		for event in events[0:5]:
			generate_photo_collages(event)
