from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.db.models import F, Count
import datetime, pytz, dateutil.parser, json, requests, random

from viewer.models import Location, LocationCountry
from viewer.forms import LocationForm
from viewer.functions.geo import get_location_address_fragment, get_location_country_code, get_location_wikidata_id
from viewer.functions.rdf import wikidata_to_wikipedia

def places(request):
	data = {}
	try:
		home = Location.objects.get(pk=settings.USER_HOME_LOCATION)
	except:
		home = None
	datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=60)
	data['home'] = home
	data['recent'] = Location.objects.filter(events__start_time__gte=datecutoff).exclude(uid=home.uid).annotate(num_events=Count('events')).order_by('-num_events')
	if home is None:
		data['overseas'] = Location.objects.none()
	else:
		data['overseas'] = Location.objects.exclude(country=None).exclude(country=home.country).order_by('label')
	data['all'] = Location.objects.annotate(num_events=Count('events')).order_by('label')
	if request.method == 'POST':
		cache.delete('dashboard')
		form = LocationForm(request.POST, request.FILES)
		if form.is_valid():
			post = form.save(commit=False)
			id = form.cleaned_data['uid']
			if form.cleaned_data.get('uploaded_image'):
				image = Image(title=post.full_label, description=post.description, image=request.FILES['uploaded_image'])
				image.save()
				post.image = request.FILES['uploaded_image']
			country = None
			country_code = get_location_country_code(post.lat, post.lon)
			if country_code != '':
				try:
					country = LocationCountry.objects.get(a2=country_code)
				except:
					country = None
				if country is None:
					country_name = get_location_address_fragment(post.lat, post.lon, 'country')
					country_wiki = wikidata_to_wikipedia(get_location_wikidata_id(post.lat, post.lon, 'country'))
					if len(country_name) > 0:
						try:
							country = LocationCountry(a2=country_code, label=country_name)
							if len(country_wiki) > 0:
								country.wikipedia = country_wiki
							country.save()
						except:
							country = None
			if not(country is None):
				post.country = country
			post.save()
			post.categories.clear()
			try:
				categories = str(request.POST['location_categories']).split(',')
			except:
				categories = []
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

