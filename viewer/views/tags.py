from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Location, Event, EventWorkoutCategory, EventTag, AutoTag, TagCondition, TagLocationCondition, TagTypeCondition, TagWorkoutCondition

def tags(request):

	data = EventTag.objects.annotate(num_events=Count('events')).order_by('-num_events')
	context = {'type':'tag', 'data':data}
	return render(request, 'viewer/pages/tags.html', context)

def tag(request, id):

	data = get_object_or_404(EventTag, id=id)
	context = {'type':'tag', 'data':data}
	return render(request, 'viewer/pages/tag.html', context)

def tagrules(request, id):

	data = get_object_or_404(EventTag, id=id)
	if request.method == 'POST':
		ret = {}
		for k in dict(request.POST).keys():
			v = request.POST[str(k)]
			if isinstance(v, list):
				if len(v) == 0:
					ret[k] = ''
				else:
					ret[k] = v[0]
			else:
				ret[k] = v
		ret['tag'] = str(data.pk)
		if 'create' in ret:
			if ret['create'] == 'rule':
				rule = AutoTag(tag=data)
				rule.save()
				return HttpResponseRedirect('../#tagrules_' + ret['tag'])
			raise Http404()
		if('tag-delete' in ret):
			# We want to delete something
			if ret['tag-delete'] == 'tag':
				# An entire tag
				try:
					t = EventTag.objects.get(id=ret['tag'])
				except:
					raise Http404()
				t.delete()
				return HttpResponseRedirect('../#tags')
		try:
			rule = AutoTag.objects.get(pk=ret['ruleid'])
		except:
			raise Http404()
		if 'cond-type' in ret:
			# Add a type condition
			n = TagTypeCondition(tag=rule, type=ret['cond-type'])
			n.save()
			return HttpResponseRedirect('../#tagrules_' + ret['tag'])
		if 'cond-workout' in ret:
			# Add a workout condition
			try:
				workout = EventWorkoutCategory.objects.get(pk=ret['cond-workout'])
			except:
				raise Http404()
			n = TagWorkoutCondition(tag=rule, workout_category=workout)
			n.save()
			return HttpResponseRedirect('../#tagrules_' + ret['tag'])
		if(('condition-lat' in ret) & ('condition-lon' in ret)):
			# Add a location condition
			n = TagLocationCondition(tag=rule, lat=ret['condition-lat'], lon=ret['condition-lon'])
			n.save()
			return HttpResponseRedirect('../#tagrules_' + ret['tag'])
		if('rule-delete' in ret):
			# We want to delete something
			if ret['rule-delete'] == 'rule':
				try:
					t = AutoTag.objects.get(id=ret['ruleid'])
				except:
					raise Http404()
				t.delete()
				return HttpResponseRedirect('../#tagrules_' + ret['tag'])
		if('cond-delete' in ret):
			# We want to delete something
			if ret['cond-delete'] == 'condition':
				# A condition
				try:
					cond = TagCondition.objects.get(pk=ret['conditionid'], tag__pk=ret['ruleid'], tag__tag__pk=ret['tag'])
				except:
					raise Http404();
				cond.delete()
				return HttpResponseRedirect('../#tagrules_' + ret['tag'])
			return HttpResponse(json.dumps(ret), content_type='application/json')
		raise Http404()
	context = {'type':'tag', 'data':data, 'workout_categories':sorted([x['id'] for x in EventWorkoutCategory.objects.all().values('id')]), 'types':sorted([x['type'] for x in Event.objects.all().values('type').distinct()])}
	return render(request, 'viewer/pages/tagrules.html', context)

def tagrule_staticmap(request, id):
	data = get_object_or_404(TagCondition, id=id)
	im = data.staticmap()
	blob = BytesIO()
	im.save(blob, 'PNG')
	return HttpResponse(blob.getvalue(), content_type='image/png')
