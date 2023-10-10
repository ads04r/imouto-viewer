from django.core.management.base import BaseCommand
from viewer.tasks import fill_cities

class Command(BaseCommand):
	"""
	Command for calling the fill_cities task from the CLI. Uses OSM to get the cities in all the countries visited, then links them to locations if possible.
	"""
	def handle(self, *args, **kwargs):

		fill_cities()
