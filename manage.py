#!/usr/bin/env python
"""Imouto's command-line utility for administrative tasks."""
import os, sys, logging

logger = logging.getLogger(__name__)

def main():
	os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imouto.settings')
	try:
		from django.core.management import execute_from_command_line
	except ImportError as exc:
		sys.stdout.write("Dependencies are not available. Please ensure you have run pip install -r requirements.txt and activated any necessary virtual environment.\n")
		sys.exit(1)
	execute_from_command_line(sys.argv)

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		logger.exception(e)
