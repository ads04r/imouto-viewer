import unittest
from pyflakes import reporter as modReporter
from pyflakes.api import checkRecursive
import sys, os

class PyFlakesTest(unittest.TestCase):
	def test_details(self):
		base_path = os.path.dirname(os.path.dirname(__file__))
		functions_path = os.path.join(base_path, 'functions')
		models_path = os.path.join(base_path, 'models')
		reporter = modReporter.Reporter(sys.stdout, open(os.devnull, 'w'))
		files = []
		for filename in os.listdir(functions_path):
			if not filename.endswith('.py'):
				continue
			files.append(os.path.join(functions_path, filename))
		ret = checkRecursive(files, reporter)
		self.assertEqual(ret, 0)

