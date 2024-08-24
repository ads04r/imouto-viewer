from django.conf import settings
import unittest, requests

class ImoutoMapsConfiguration(unittest.TestCase):
	def test_details(self):
		self.assertEqual(hasattr(settings, "MAP_TILES"), True)
		self.assertEqual(hasattr(settings, "MAPBOX_API_KEY"), True)

class ImoutoBaseConfiguration(unittest.TestCase):
	def test_details(self):
		self.assertEqual(hasattr(settings, "DEFAULT_FONT"), True)
		self.assertEqual(hasattr(settings, "PHOTO_COLLAGE_MAX_PHOTOS"), True)
		self.assertEqual(hasattr(settings, "RDF_NAMESPACE"), True)
		loc_manager_exists = hasattr(settings, "LOCATION_MANAGER_URL")
		self.assertEqual(loc_manager_exists, True)
		if loc_manager_exists:
			self.assertEqual(hasattr(settings, "LOCATION_MANAGER_TOKEN"), True)
			url = settings.LOCATION_MANAGER_URL
			r = requests.get(url)
			self.assertEqual(r.status_code, 200)
			try:
				data = r.json()
			except:
				data = {}
			self.assertEqual(('event' in data), True)
			self.assertEqual(('position' in data), True)
			self.assertEqual(('route' in data), True)
			self.assertEqual(('elevation' in data), True)
			self.assertEqual(('process' in data), True)
			self.assertEqual(('bbox' in data), True)

class ImoutoUserConfiguration(unittest.TestCase):
	def test_details(self):
		self.assertEqual(hasattr(settings, "USER_HOME_LOCATION"), True)
		self.assertEqual(hasattr(settings, "USER_DATE_OF_BIRTH"), True)
		self.assertEqual(hasattr(settings, "USER_HOME_LOCATION"), True)
		self.assertEqual(hasattr(settings, "USER_HOME_URI"), True)
		self.assertEqual(hasattr(settings, "USER_RDF_NAMESPACE"), True)
