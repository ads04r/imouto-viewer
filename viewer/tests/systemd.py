import unittest, subprocess

class ProcessQueueTest(unittest.TestCase):
	def test_details(self):
		retcode = subprocess.call(["systemctl", "is-active", "--quiet", "imouto-queue-process"])
		self.assertEqual(retcode, 0)

class ReportQueueTest(unittest.TestCase):
	def test_details(self):
		retcode = subprocess.call(["systemctl", "is-active", "--quiet", "imouto-queue-reports"])
		self.assertEqual(retcode, 0)
