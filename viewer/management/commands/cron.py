from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import DataReading, Event
from io import StringIO
import os, sys, datetime, shutil, sqlite3, pytz, csv, xmltodict, json
from viewer.tasks.imports import check_watched_directories
from viewer.tasks.process import generate_location_events

class Command(BaseCommand):
	"""
	Command to run the cron tasks
	"""
	def handle(self, *args, **kwargs):

		check_watched_directories()
		generate_location_events()
