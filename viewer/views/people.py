from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.db.models import F, Max, Count
from django.db.models.functions import Cast
from django.db.models.fields import DateField
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Person, RemoteInteraction

from viewer.functions.people import explode_properties

def people(request):
	data = {}
	datecutoff = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=365)
	data['recent_by_events'] = Person.objects.filter(event__start_time__gte=datecutoff).annotate(num_events=Count('event', distinct=True)).order_by('-num_events')[0:10]
	data['recent_by_days'] = Person.objects.filter(event__start_time__gte=datecutoff).annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).order_by('-days')[0:10]
	data['recent_by_last_seen'] = Person.objects.annotate(last_seen=Max('event__start_time')).order_by('-last_seen')[0:10]
	data['photos'] = Person.objects.filter(photo__time__gte=datecutoff).annotate(photo_count=Count('photo')).order_by('-photo_count')[0:10]
	data['messages'] = []
	data['calls'] = []
	for number in RemoteInteraction.objects.filter(time__gte=datecutoff, type='sms').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['messages'].append([person, number['messages']])
	for number in RemoteInteraction.objects.filter(time__gte=datecutoff, type='phone-call').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
		try:
			person = Person.objects.get(properties__key='phone', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
	data['all'] = Person.objects.annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).annotate(last_seen=Max('event__start_time')).order_by('given_name', 'family_name')
	context = {'type':'person', 'data':data}
	ret = render(request, 'viewer/pages/people.html', context)
	return ret

def person(request, uid):
	key = 'person_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
	ret = cache.get(key)
	if ret is None:
		data = get_object_or_404(Person, uid=uid)
		context = {'type':'person', 'data':data, 'properties':explode_properties(data)}
		ret = render(request, 'viewer/pages/person.html', context)
		cache.set(key, ret, timeout=86400)
	return ret

def person_photo(request, uid):
	data = get_object_or_404(Person, uid=uid)
	im = data.photo()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def person_json(request, uid):
	data = get_object_or_404(Person, uid=uid)
	response = HttpResponse(json.dumps(data.to_dict()), content_type='application/json')
	return response

def person_thumbnail(request, uid):
	data = get_object_or_404(Person, uid=uid)
	im = data.thumbnail(100)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response
