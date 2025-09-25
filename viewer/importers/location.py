import requests

import logging
logger = logging.getLogger(__name__)

def upload_file(user, temp_file, file_source, format=''):
	"""
	Uploads a file to the configured location manager. When calling this function you need to pass a string
	representing the source of the data (eg 'handheld_gps', 'fitness_tracker', 'phone').

	:param temp_file: The path of the file being sent.
	:param file_source: A string representing the source of the data.
	:param format: Currently unused.
	:return: True if the upload was successful, False if not.
	:rtype: bool
	"""
	address = user.profile.settings['LOCATION_MANAGER_URL']
	bearer_token = user.profile.settings['LOCATION_MANAGER_TOKEN']
	url = address.rstrip('/') + '/import'
	if format == '':
		r = requests.post(url, headers={'Authorization': 'Token ' + bearer_token}, data={'file_source': file_source}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	else:
		r = requests.post(url, headers={'Authorization': 'Token ' + bearer_token}, data={'file_source': file_source, 'file_format': format}, files={'uploaded_file': (temp_file, open(temp_file, 'rb'))})
	if r.status_code == 200:
		return True
	return False

