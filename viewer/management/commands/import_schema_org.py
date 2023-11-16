from django.core.management.base import BaseCommand
from viewer.functions.schema_org import import_schema_org, match_categories

class Command(BaseCommand):
	"""
	Command for importing the latest schema.org vocabulary and matching the classes within to Imouto location categories.
	"""
	def handle(self, *args, **kwargs):

		import_schema_org()
		match_categories()
