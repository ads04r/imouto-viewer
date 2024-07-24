from django.core.management.base import BaseCommand
from viewer.functions.schema_org import import_schema_org, match_categories

class Command(BaseCommand):
	"""
	Command for importing the latest schema.org vocabulary and matching the classes within to Imouto location categories.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-u", "--url", action="store", dest="url", default="", help="")
		parser.add_argument("-l", "--lang", action="store", dest="lang", default="en", help="")

	def handle(self, *args, **kwargs):

		url = kwargs['url']
		lang = kwargs['lang']
		if url == '':
			import_schema_org(lang=lang)
		else:
			import_schema_org(url=url, lang=lang)
		match_categories()
