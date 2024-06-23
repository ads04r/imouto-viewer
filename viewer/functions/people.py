from viewer.models import Event, Person, PersonProperty

import logging
logger = logging.getLogger(__name__)

def explode_properties(person):
	prop = {}
	for k in person.get_properties():
		if k == 'mhb':
			continue
		if k == 'image':
			continue
		if k == 'livesat':
			continue
		if k == 'birthday':
			continue
		if k == 'hasface':
			continue
		v = person.get_property(k)
		prop[k] = v
	return prop

def bubble_event_people():

	for event in Event.objects.filter(type='life_event'):
		for e in event.subevents():
			for person in e.people.all():
				event.people.add(person)

def find_person_by_picasaid(picasaid, name=''):

	try:
		prop = PersonProperty.objects.get(key='hasface', value=picasaid)
		ret = prop.person
	except:
		ret = None

	if not(ret is None):
		return ret

	if name != '':

		for person in Person.objects.all():
			fn = person.full_name()
			if fn == name:
				ret = person
				break

	if not(ret is None):
		prop = PersonProperty(person=ret, key='hasface', value=picasaid)
		prop.save()

	return ret

