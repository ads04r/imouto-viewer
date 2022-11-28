import datetime, pytz, json, sys, requests, os
from viewer.models import *
from django.core.cache import cache
from django.conf import settings
from dateutil import parser

def __find_person_by_monica_hash(hash):

	for item in get_monica_contact_data():
		if not('hash_id' in item):
			continue
		if item['hash_id'] == hash:
			return item
	return []

def create_monica_call(content, person, date, incoming=False):

	hashes = person.get_property('monicahash')
	if len(hashes) == 0:
		return False
	item = __find_person_by_monica_hash(hashes[0])
	if not('id' in item):
		return False
	contact_id = item['id']

	try:
		url = settings.MONICA_URL.lstrip('/') + '/calls'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	if url == '':
		return []
	if token == '':
		return []

	data = {'content': content, 'called_at': date.strftime("%Y-%m-%d"), 'contact_id': contact_id, 'contact_called': incoming}
	r = requests.request("POST", url, headers={'Authorization': 'Bearer ' + token}, json=data)
	ret = json.loads(r.text)
	if not('data' in ret):
		return False
	if not('id' in ret['data']):
		return False

	key = 'monica_call_data'
	cache.delete(key)
	return True

def delete_monica_activity(activity_id):

	try:
		url = settings.MONICA_URL.lstrip('/') + '/activities/' + str(activity_id)
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	if url == '':
		return []
	if token == '':
		return []

	r = requests.request("DELETE", url, headers={'Authorization': 'Bearer ' + token})
	ret = json.loads(r.text)
	if not('deleted' in ret):
		return False
	if not('id' in ret):
		return False
	return ret['deleted']

def delete_monica_activities():

	data = get_monica_activity_data()
	ret = 0

	for item in data:
		if delete_monica_activity(item['id']):
			ret = ret + 1

	key = 'monica_activity_data'
	cache.delete(key)
	return ret

def create_monica_activity_from_event(event):

	return create_monica_activity(event.caption, event.start_time, event.people.all())

def create_monica_activity(summary, date, people):

	contacts = []
	for person in people:
		hashes = person.get_property('monicahash')
		if len(hashes) == 0:
			continue
		item = __find_person_by_monica_hash(hashes[0])
		if not('id' in item):
			continue
		id = item['id']
		contacts.append(id)
	if len(contacts) == 0:
		return []
	try:
		url = settings.MONICA_URL.lstrip('/') + '/activities'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	if url == '':
		return []
	if token == '':
		return []

	data = {'summary': summary, 'happened_at': date.strftime("%Y-%m-%d"), 'contacts': contacts}
	r = requests.request("POST", url, headers={'Authorization': 'Bearer ' + token}, json=data)
	ret = json.loads(r.text)
	if not('data' in ret):
		return False
	if not('id' in ret['data']):
		return False

	key = 'monica_activity_data'
	cache.delete(key)
	return True

def assign_monica_avatar(hash, file, force=True):

	try:
		url = settings.MONICA_URL.lstrip('/') + '/photos'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	item = __find_person_by_monica_hash(hash)
	if not('id' in item):
		return False
	id = item['id']
	current_avatar = item['information']['avatar']['source']
	if current_avatar == 'photo':
		if not(force):
			return False
	if url == '':
		return False
	if token == '':
		return False
	files = [('photo', (file, open(file, 'rb'), 'image/jpeg'))]
	data = {'contact_id': id}
	r = requests.request("POST", url, headers={'Authorization': 'Bearer ' + token}, data=data, files=files)
	ret = json.loads(r.text)
	if not('data' in ret):
		return False
	if not('id' in ret['data']):
		return False
	photo_id = ret['data']['id']
	url = settings.MONICA_URL.lstrip('/') + '/contacts/' + str(id) + '/avatar'
	data = {'source': 'photo', 'photo_id': photo_id}
	r = requests.request("PUT", url, headers={'Authorization': 'Bearer ' + token}, data=data)
	ret = json.loads(r.text)
	if not('data' in ret):
		return False
	if not('hash_id' in ret['data']):
		return False

	if ret['data']['hash_id'] == hash:
		key = 'monica_contact_data'
		cache.delete(key)
		return True

	return False

def get_last_monica_activity():

	dt = datetime.date(1970, 1, 1)
	for act in get_monica_activity_data():
		if not('happened_at' in act):
			continue
		ds = act['happened_at'].split('-')
		if len(ds) != 3:
			continue
		dtc = datetime.date(int(ds[0]), int(ds[1]), int(ds[2]))
		if dtc > dt:
			dt = dtc
	return dt

def get_last_monica_call():

	dt = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
	for act in get_monica_call_data():
		if not('called_at' in act):
			continue
		dtc = parser.parse(act['called_at'])
		if dtc > dt:
			dt = dtc
	return dt

def get_monica_activity_data():

	key = 'monica_activity_data'
	data = cache.get(key)
	if not(data is None):
		return data

	try:
		url = settings.MONICA_URL.lstrip('/') + '/activities'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	data = []
	if url == '':
		return ret
	if token == '':
		return ret
	page = 1
	while True:
		r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'page': page})
		data_ret = json.loads(r.text)
		if not(isinstance(data_ret, (dict))):
			break
		if not('data' in data_ret):
			break
		if len(data_ret['data']) == 0:
			break
		data = data + data_ret['data']
		page = page + 1

	cache.set(key, data, timeout=300)

	return data

def get_monica_contact_data():

	key = 'monica_contact_data'
	data = cache.get(key)
	if not(data is None):
		return data

	try:
		url = settings.MONICA_URL.lstrip('/') + '/contacts'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	data = []
	if url == '':
		return ret
	if token == '':
		return ret
	page = 1
	while True:
		r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'with': 'contactfields', 'page': page})
		data_ret = json.loads(r.text)
		if not(isinstance(data_ret, (dict))):
			break
		if not('data' in data_ret):
			break
		if len(data_ret['data']) == 0:
			break
		data = data + data_ret['data']
		page = page + 1

	cache.set(key, data, timeout=300)

	return data

def get_monica_journal_data():

	key = 'monica_journal_data'
	data = cache.get(key)
	if not(data is None):
		return data

	try:
		url = settings.MONICA_URL.lstrip('/') + '/journal'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	data = []
	if url == '':
		return ret
	if token == '':
		return ret
	page = 1
	while True:
		r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'with': 'contactfields', 'page': page})
		data_ret = json.loads(r.text)
		if not(isinstance(data_ret, (dict))):
			break
		if not('data' in data_ret):
			break
		if len(data_ret['data']) == 0:
			break
		data = data + data_ret['data']
		page = page + 1

	cache.set(key, data, timeout=300)

	return data

def get_monica_call_data():

	key = 'monica_call_data'
	data = cache.get(key)
	if not(data is None):
		return data

	try:
		url = settings.MONICA_URL.lstrip('/') + '/calls'
	except AttributeError:
		url = ''
	try:
		token = settings.MONICA_PERSONAL_TOKEN
	except AttributeError:
		token = ''
	data = []
	if url == '':
		return ret
	if token == '':
		return ret
	page = 1
	while True:
		r = requests.get(url, headers={'Authorization': 'Bearer ' + token}, params={'page': page})
		data_ret = json.loads(r.text)
		if not(isinstance(data_ret, (dict))):
			break
		if not('data' in data_ret):
			break
		if len(data_ret['data']) == 0:
			break
		data = data + data_ret['data']
		page = page + 1

	cache.set(key, data, timeout=300)

	return data

