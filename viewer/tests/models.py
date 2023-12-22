import unittest, viewer.models
from django.test import Client
from django.db import connection, connections

class ModelTest(unittest.TestCase):
	def setUp(self):
		self.models = ['WeekdayLookup','WeatherLocation','WeatherReading','LocationCountry','Location','LocationProperty','Person','Photo','PersonPhoto','RemoteInteraction','PersonProperty','DataReading','Event','LifePeriod','PhotoCollage','PersonEvent','Media','MediaEvent','EventSimilarity','EventWorkoutCategory','EventWorkoutCategoryStat','EventTag','CalendarFeed','CalendarAppointment','PersonCategory','LocationCategory','Day','AutoTag','TagCondition','TagLocationCondition','TagTypeCondition','TagWorkoutCondition']
	def test_details(self):
		for model_name in self.models:
			raised = False
			try:
				x = getattr(viewer.models, model_name)
			except:
				raised = True
			self.assertFalse(raised, model_name + " could not be instantiated.")
