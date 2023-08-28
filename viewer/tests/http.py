import unittest
from django.test import Client

class RootTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		r = self.client.get('/')
		self.assertEqual(r.status_code, 302)
		r = self.client.get('/viewer/')
		self.assertEqual(r.status_code, 200)

