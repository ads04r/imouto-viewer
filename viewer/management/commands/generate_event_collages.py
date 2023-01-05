from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from viewer.models import Event, PhotoCollage
from viewer.tasks import generate_photo_collages
from random import shuffle
import datetime, pytz, os

class Command(BaseCommand):
	"""
	Command for finding events that will be included in life reports, and calling the collage generation script for these events.
	"""
	def handle(self, *args, **kwargs):

		min_photos = 3
		dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
		dts = dt - datetime.timedelta(days=365)
		dte = dt - datetime.timedelta(days=7)

		collages = []
		events = []
		for collage in PhotoCollage.objects.all():
			if not(os.path.exists(collage.image.path)):
				collages.append(collage)
				continue
			if collage.image.size < 1000:
				collage.image.delete()
				collages.append(collage)

		for collage in collages:
			if not(collage.event is None):
				if not(collage.event in events):
					events.append(collage.event)
			collage.delete()

		for e in Event.objects.filter(photo_collages=None, end_time__gte=dts, start_time__lte=dte).exclude(type='life_event').order_by("?"):
			if len(events) >= 5:
				break
			if e.photos().count() < min_photos:
				continue
			if not(e in events):
				events.append(e)

		for event in events:
			print(event)
			generate_photo_collages(event.id)
