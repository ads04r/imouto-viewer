from django.core.management.base import BaseCommand
from viewer.tasks.process import calculate_journey_distances

class Command(BaseCommand):
	"""
	Command for calling the calculate_journey_distances task from the CLI. Checks for journey Events without a cached distance value, and pre-caches the ones it finds.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-m", "--max", type=int, action="store", dest="max", default=200, required=False, help="Allows the user to specify a maximum number of Events to pre-cache before stopping.")

	def handle(self, *args, **kwargs):

		calculate_journey_distances(kwargs['max'])
