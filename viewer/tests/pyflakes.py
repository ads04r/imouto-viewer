import unittest
from pyflakes import reporter as modReporter
from pyflakes.api import checkRecursive

class PyFlakesTest(unittest.TestCase):
	def test_details(self):
		self.assertEqual((2 + 2), 4)
