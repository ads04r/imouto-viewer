from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, F, DurationField, ExpressionWrapper
from django.utils.text import slugify
from django.conf import settings
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Event, DataReading, EventWorkoutCategory, Day
from viewer.forms import WorkoutCategoryForm

from viewer.functions.health import get_sleep_history
from viewer.functions.utils import imouto_json_serializer

def health_data(datatypes):
	item = {'date': ''}
	filter = None
	ret = []
	for type in datatypes:
		if filter is None:
			filter = Q(type=type)
		else:
			filter = filter | Q(type=type)
	for dr in DataReading.objects.filter(filter).order_by('-start_time'):
		type = str(dr.type)
		if type == 'weight':
			value = float(dr.value) / 1000
		else:
			value = int(dr.value)
		if dr.start_time != item['date']:
			if item['date'] != '':
				ret.append(item)
			item = {'date': dr.start_time}
		item[type] = value
	ret.append(item)
	return ret

@csrf_exempt
def health(request, pageid):
	context = {'type':'view', 'page': pageid, 'data':[]}
	if pageid == 'heart':
		return render(request, 'viewer/pages/health_heart.html', context)
	if pageid == 'sleep':
		dt = pytz.utc.localize(datetime.datetime.utcnow())
		dt_start = (dt - datetime.timedelta(days=365)).date()
		context['data'] = {'stats': [], 'days': Day.objects.filter(date__gte=dt_start).order_by('-date')}
		return render(request, 'viewer/pages/health_sleep.html', context)
	if pageid == 'distance':
		return render(request, 'viewer/pages/health_distance.html', context)
	if pageid == 'exercise':
		if request.method == 'POST':
			form = WorkoutCategoryForm(request.POST)
			if form.is_valid():
				cache.delete('dashboard')
				if 'id' in request.POST:
					id = str(request.POST['id'])
				else:
					id = ''
				label = str(request.POST['label'])
				comment = str(request.POST['comment'])

				if id == '':
					data = EventWorkoutCategory(id=slugify(label.lower()))
				else:
					data = get_object_or_404(EventWorkoutCategory, id=id)
				data.label = label
				data.comment = comment
				data.save()

				return HttpResponseRedirect('../#workout_' + str(data.id))
		else:
			context['data'] = EventWorkoutCategory.objects.all()
			context['form'] = WorkoutCategoryForm()
			return render(request, 'viewer/pages/health_exercise.html', context)
	if pageid == 'blood':
		if request.method == 'POST':
			ret = json.loads(request.body)
			dt = datetime.datetime.now(pytz.utc)
			datapoint = DataReading(type='bp_sys', start_time=dt, end_time=dt, value=ret['bp_sys_val'])
			datapoint.save()
			datapoint = DataReading(type='bp_dia', start_time=dt, end_time=dt, value=ret['bp_dia_val'])
			datapoint.save()
			response = HttpResponse(json.dumps(ret), content_type='application/json')
			return response
		context['data'] = health_data(['bp_sys', 'bp_dia'])
		return render(request, 'viewer/pages/health_bp.html', context)
	if pageid == 'weight':
		if request.method == 'POST':
			ret = json.loads(request.body)
			dt = datetime.datetime.now(pytz.utc)
			value = float(ret['weight_val'])
			value_unit = float(ret['weight_unit'])
			value_grams = value * value_unit
			datapoint = DataReading(type='weight', start_time=dt, end_time=dt, value=value_grams)
			datapoint.save()
			response = HttpResponse(json.dumps(ret), content_type='application/json')
			return response
		context['data'] = health_data(['weight', 'fat', 'muscle', 'water'])
		context['graphs'] = {}
		dt = pytz.utc.localize(datetime.datetime.now()).replace(hour=0, minute=0, second=0)
		for i in [{'label': 'week', 'dt': (dt - datetime.timedelta(days=7))}, {'label': 'month', 'dt': (dt - datetime.timedelta(days=28))}, {'label': 'year', 'dt': (dt - datetime.timedelta(days=365))}]:
			item = []
			min_dt = i['dt'].timestamp()
			for point in DataReading.objects.filter(type='weight', end_time__gte=i['dt']).order_by('start_time'):
				pdt = point.start_time.timestamp()
				if pdt < min_dt:
					continue
				item.append({'x': pdt, 'y': (float(point.value) / 1000)})
			context['graphs'][i['label']] = json.dumps(item)
		return render(request, 'viewer/pages/health_weight.html', context)
	if pageid == 'mentalhealth':
		if request.method == 'POST':
			ret = json.loads(request.body)
			dt = pytz.utc.localize(datetime.datetime.utcnow())
			datapoint = DataReading(type='hads-a', start_time=dt, end_time=dt, value=ret['anxiety'])
			datapoint.save()
			datapoint = DataReading(type='hads-d', start_time=dt, end_time=dt, value=ret['depression'])
			datapoint.save()
			response = HttpResponse(json.dumps(ret), content_type='application/json')
			return response
		for entry in health_data(['hads-a', 'hads-d']):
			item = {'date': entry['date']}
			if 'hads-a' in entry:
				item['anxiety'] = entry['hads-a']
			if 'hads-d' in entry:
				item['depression'] = entry['hads-d']
			context['data'].append(item)
		return render(request, 'viewer/pages/health_mentalhealth.html', context)
	return render(request, 'viewer/pages/health.html', context)

@csrf_exempt
def mood(request):
	if request.method != 'POST':
		raise Http404()
	data = json.loads(request.body)
	if not('mood' in data):
		raise Http404()
	m = 0
	if data['mood'] == 'unhappy':
		m = 1
	if data['mood'] == 'neutral':
		m = 3
	if data['mood'] == 'happy':
		m = 5
	if m == 0:
		raise Http404()
	dt = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone(settings.TIME_ZONE))
	entry = DataReading(start_time=dt, end_time=dt, type='mood', value=m)
	entry.save()
	ret = {"date": dt, "mood": m, "created": entry.pk}
	response = HttpResponse(json.dumps(ret, default=imouto_json_serializer), content_type='application/json')
	return response

def workout(request, id):

	data = get_object_or_404(EventWorkoutCategory, id=id)
	context = {'type':'workout', 'data':data}
	return render(request, 'viewer/pages/workout.html', context)

@csrf_exempt
def workoutdelete(request, id):
	cache.delete('dashboard')
	if request.method != 'POST':
		raise Http404()
	data = get_object_or_404(EventWorkoutCategory, id=id)
	ret = data.delete()
	response = HttpResponse(json.dumps(ret), content_type='application/json')
	return response

