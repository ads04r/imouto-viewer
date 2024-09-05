import unittest
from pyflakes import reporter as modReporter
from pyflakes.api import checkRecursive
import sys, os

class FunctionsStyleTest(unittest.TestCase):
	def test_details(self):
		base_path = os.path.dirname(os.path.dirname(__file__))
		functions_path = os.path.join(base_path, 'functions')
		reporter = modReporter.Reporter(sys.stdout, open(os.devnull, 'w'))
		files = []
		for filename in os.listdir(functions_path):
			if not filename.endswith('.py'):
				continue
			files.append(os.path.join(functions_path, filename))
		ret = checkRecursive(files, reporter)
		self.assertEqual(ret, 0)

class ModelsStyleTest(unittest.TestCase):
	def test_details(self):
		base_path = os.path.dirname(os.path.dirname(__file__))
		models_path = os.path.join(base_path, 'models')
		reporter = modReporter.Reporter(sys.stdout, open(os.devnull, 'w'))
		files = []
		for filename in os.listdir(models_path):
			if not filename.endswith('.py'):
				continue
			if filename == '__init__.py':
				continue
			files.append(os.path.join(models_path, filename))
		ret = checkRecursive(files, reporter)
		self.assertEqual(ret, 0)

class ImportersStyleTest(unittest.TestCase):
	def test_details(self):
		base_path = os.path.dirname(os.path.dirname(__file__))
		importers_path = os.path.join(base_path, 'importers')
		reporter = modReporter.Reporter(sys.stdout, open(os.devnull, 'w'))
		files = []
		for filename in os.listdir(importers_path):
			if not filename.endswith('.py'):
				continue
			files.append(os.path.join(importers_path, filename))
		ret = checkRecursive(files, reporter)
		self.assertEqual(ret, 0)

