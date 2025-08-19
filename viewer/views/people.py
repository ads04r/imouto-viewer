from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.db.models import F, Max, Count
from django.db.models.functions import Cast
from django.db.models.fields import DateField
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Person, RemoteInteraction, Location, PersonProperty
from viewer.forms import PersonForm
from viewer.functions.people import explode_properties

import logging
logger = logging.getLogger(__name__)

def people(request):
	data = {}
	datecutoff = pytz.utc.localize(datetime.datetime.utcnow()) - datetime.timedelta(days=365)
	data['recent_by_events'] = Person.objects.filter(user=request.user, event__start_time__gte=datecutoff).annotate(num_events=Count('event', distinct=True)).order_by('-num_events')[0:10]
	data['recent_by_days'] = Person.objects.filter(user=request.user, event__start_time__gte=datecutoff).annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).order_by('-days')[0:10]
	data['recent_by_last_seen'] = Person.objects.filter(user=request.user).annotate(last_seen=Max('event__start_time')).order_by('-last_seen')[0:10]
	data['photos'] = Person.objects.filter(user=request.user, photo__time__gte=datecutoff).annotate(photo_count=Count('photo')).order_by('-photo_count')[0:10]
	data['messages'] = []
	data['calls'] = []
	for number in RemoteInteraction.objects.filter(user=request.user, time__gte=datecutoff, type='sms').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(user=request.user, properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['messages'].append([person, number['messages']])
	for number in RemoteInteraction.objects.filter(user=request.user, time__gte=datecutoff, type='phone-call').values('address').annotate(messages=Count('address')).order_by('-messages'):
		try:
			person = Person.objects.get(user=request.user, properties__key='mobile', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
		try:
			person = Person.objects.get(user=request.user, properties__key='phone', properties__value=number['address'])
		except:
			person = None
		if not(person is None):
			data['calls'].append([person, number['messages']])
	data['all'] = Person.objects.annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).annotate(last_seen=Max('event__start_time')).order_by('display_name')
	data['deceased'] = Person.objects.filter(user=request.user, significant=True, properties__key='deathday').annotate(days=Count(Cast('event__start_time', DateField()), distinct=True)).annotate(last_seen=Max('event__start_time')).order_by('display_name')
	if request.method == 'POST':
		cache.delete('dashboard')
		form = PersonForm(request.POST, request.FILES)
		if form.is_valid():
			post = form.save(commit=False)
			id = form.cleaned_data['uid']
			if form.cleaned_data.get('image'):
				post.image = request.FILES['image']
			post.save()
			try:
				person_home = request.POST['home']
			except:
				person_home = form.cleaned_data.get('home')
			if person_home:
				loc = Location.objects.get(user=request.user, uid=person_home)
				pp = PersonProperty(person=post, key='livesat', value=loc.pk)
				pp.save()
			for p in [('birthday', 'birthday'), ('homephone', 'phone'), ('workphone', 'work'), ('mobilephone', 'mobile')]:
				try:
					person_value = request.POST[p[0]]
				except:
					person_value = form.cleaned_data.get(p[0])
				if person_value:
					pp = PersonProperty(person=post, key=p[1], value=person_value)
					pp.save()
			return HttpResponseRedirect('./#person_' + str(id))
		else:
			raise Http404(form.errors)
	else:
		form = PersonForm()
	context = {'type':'person', 'data':data, 'form':form, 'places':Location.objects.filter(user=request.user).values('uid', 'label').order_by('label')}
	ret = render(request, 'viewer/pages/people.html', context)
	return ret

def person(request, uid):

	key = 'person_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
	if request.method == 'POST':
		data = get_object_or_404(Person, uid=uid)
		cache.delete('dashboard')
		cache.delete(key)
		form = PersonForm(request.POST, request.FILES, instance=data)

		if form.is_valid():
			post = form.save(commit=False)
			id = form.cleaned_data['uid']
			if form.cleaned_data.get('uploaded_image'):
				post.image = request.FILES['uploaded_image']
			post.save()
			return HttpResponseRedirect('../#person_' + str(id))
		else:
			raise Http404(form.errors)

	ret = cache.get(key)
	if ret is None:
		data = get_object_or_404(Person, uid=uid)
		form = PersonForm(instance=data)
		ignore = ['mhb', 'image', 'livesat', 'birthday', 'deathday', 'hasface']
		context = {'type':'person', 'data':data, 'form':form, 'properties': explode_properties(data), 'property_keys': [item for item in sorted(list(map(lambda x: x['key'], list(PersonProperty.objects.values('key').distinct())))) if item not in ignore]}
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

def person_property(request, uid):
	if request.method == 'POST':
		person = get_object_or_404(Person, uid=uid)
		key = 'person_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
		cache.delete(key)
		if 'property-key' in request.POST:
			values = []
			append = False
			k = request.POST['property-key']
			if 'property-value' in request.POST:
				for v in request.POST['property-value'].strip().split('\n'):
					values.append(v.strip())
			if 'property-append' in request.POST:
				if int(request.POST['property-append']) == 1:
					append = True

			if not append:
				PersonProperty.objects.filter(person=person, key=k).delete()
			for v in values:
				try:
					pp = PersonProperty.objects.get(person=person, key=k, value=v)
				except:
					pp = PersonProperty(person=person, key=k, value=v)
					pp.save()
			return HttpResponseRedirect('../../#person_' + str(person.uid))
	raise Http404()
