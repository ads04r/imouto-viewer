from django.core.management.base import BaseCommand
from viewer.tasks.process import fill_countries

class Command(BaseCommand):
	"""
	Command for calling the fill_countries task from the CLI.
	"""
	def handle(self, *args, **kwargs):

		fill_countries()
