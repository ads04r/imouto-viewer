from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from viewer.models import Event, Location
from viewer.functions.people import bubble_event_people
from viewer.functions.locations import create_location_events
import os, sys, datetime, pytz, csv, socket, json, urllib, re, random, sys, urllib.request

class Command(BaseCommand):
	"""
	Command for generating location events from existing GPS data.
	"""
	def add_arguments(self, parser):

		parser.add_argument("-l", "--min-length", action="store", dest="minlength", default="300", help="The minimum length (in seconds) that an event can be. Any period of time spent at a location for less than this is ignored.")

	def handle(self, *args, **kwargs):

		min_duration = int(kwargs['minlength'])

		for ev in create_location_events(min_duration):
			dtlen = (ev.end_time - ev.start_time).total_seconds()
			sys.stderr.write(self.style.SUCCESS(str(ev.start_time) + " - " + str(ev.location) + " " + str(int(dtlen / 60)) + '\n'))

		bubble_event_people()
