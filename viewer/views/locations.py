from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.db.models import F, Count
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Location
from viewer.forms import LocationForm

def places(request):
	data = {}
	datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=60)
	data['recent'] = Location.objects.filter(events__start_time__gte=datecutoff).annotate(num_events=Count('events')).order_by('-num_events')
	data['all'] = Location.objects.annotate(num_events=Count('events')).order_by('label')
	if request.method == 'POST':
		cache.delete('dashboard')
		form = LocationForm(request.POST, request.FILES)
		if form.is_valid():
			post = form.save(commit=False)
			id = form.cleaned_data['uid']
			if form.cleaned_data.get('uploaded_image'):
				#image = Image(title=post.full_label, description=post.description, image=request.FILES['uploaded_image'])
				#image.save()
				post.image = request.FILES['uploaded_image']
			post.save()
			post.categories.clear()
			try:
				categories = str(request.POST['location_categories']).split(',')
			except:
				categproes = []
			for category in categories:
				post.add_category(category.strip())

			return HttpResponseRedirect('./#place_' + str(id))
		else:
			raise Http404(form.errors)
	else:
		form = LocationForm()
	context = {'type':'place', 'data':data, 'form':form}
	return render(request, 'viewer/pages/places.html', context)

def place(request, uid):
	key = 'place_' + str(uid) + '_' + datetime.date.today().strftime("%Y%m%d")
	ret = cache.get(key)
	if ret is None:
		data = get_object_or_404(Location, uid=uid)
		context = {'type':'place', 'data':data}
		ret = render(request, 'viewer/pages/place.html', context)
		cache.set(key, ret, timeout=86400)
	return ret

def place_photo(request, uid):
	data = get_object_or_404(Location, uid=uid)
	im = data.photo()
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def place_thumbnail(request, uid):
	data = get_object_or_404(Location, uid=uid)
	im = data.thumbnail(100)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response

def place_json(request, uid):
	data = get_object_or_404(Location, uid=uid)
	data_dict = data.to_dict()
	data_dict['internal_id'] = data.pk
	response = HttpResponse(json.dumps(data_dict), content_type='application/json')
	return response
