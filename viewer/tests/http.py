import unittest
from django.test import Client
from django.db import connection, connections

class RootTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/')
		self.assertEqual(r.status_code, 302)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/')
		self.assertEqual(r.status_code, 200)

class JavascriptTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/script/imouto.js')
		self.assertEqual(r.status_code, 200)

class JSONTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/reports.json')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/stats.json')
		self.assertEqual(r.status_code, 200)

class JSONQueuesTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/process')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/import')
		self.assertEqual(r.status_code, 200)

class StaticPagesTest(unittest.TestCase):
	def setUp(self):
		self.client = Client()
	def test_details(self):
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/stats.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/onthisday.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/upload.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/timeline.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/tags.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/events.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/places.html')
		self.assertEqual(r.status_code, 200)
		if connection.connection and not connection.is_usable():
			del connections._connections.default
		r = self.client.get('/viewer/people.html')
		self.assertEqual(r.status_code, 200)

