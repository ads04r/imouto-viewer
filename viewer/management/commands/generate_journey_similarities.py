from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from background_task.models import Task
from viewer.tasks.datacrunching import generate_similar_events

class Command(BaseCommand):
	"""
	Command for generating journey comparison data.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-e", "--max-events", action="store", dest="maxevents", default="10", help="The maximum number of events for which to generate similarity data. Remember this is an order N squared function; the value defaults to 10, and every time this is incremented the time for this function to run will more than double.")

	def handle(self, *args, **kwargs):

		max_events = int(kwargs['maxevents'])
		existing_tasks = Task.objects.filter(task_name='viewer.tasks.generate_similar_events').count()

		if existing_tasks == 0:
			task = generate_similar_events(max_events)
