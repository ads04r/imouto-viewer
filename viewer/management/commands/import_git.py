from django.core.management.base import BaseCommand
from viewer.importers import import_github_history
import sys

class Command(BaseCommand):
	"""
	Command for calling the import github function from the CLI
	"""
	def handle(self, *args, **kwargs):

		for c in import_github_history():
			sys.stderr.write(self.style.SUCCESS('Imported commit ' + c.hash + ' in ' + c.repo_url + '\n'))
