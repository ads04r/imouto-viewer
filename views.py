from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
import datetime, pytz, dateutil.parser

from .models import *
from .forms import *
from .functions import *

def index(request):
    context = {'type':'index', 'data':[]}
    return render(request, 'viewer/index.html', context)

def dashboard(request):
    data = generate_dashboard()
    context = {'type':'view', 'data':data}
    return render(request, 'viewer/dashboard.html', context)    

def timeline(request):
    dt = Event.objects.order_by('-start_time')[0].start_time
    ds = dt.strftime("%Y%m%d")
    context = {'type':'view', 'data':{'current': ds}}
    return render(request, 'viewer/timeline.html', context)    

def timelineitem(request, ds):
    dsyear = int(ds[0:4])
    dsmonth = int(ds[4:6])
    dsday = int(ds[6:])
    dtq = datetime.datetime(dsyear, dsmonth, dsday, tzinfo=pytz.UTC)
    events = Event.objects.filter(start_time__gte=dtq).filter(start_time__lt=(dtq + datetime.timedelta(hours=24))).order_by('-start_time')

    dtn = Event.objects.filter(start_time__lt=dtq).order_by('-start_time')[0].start_time
    dsn = dtn.strftime("%Y%m%d")
    
    context = {'type':'view', 'data':{'label': dtq.strftime("%A %-d %B"), 'next': dsn, 'events': events}}
    return render(request, 'viewer/timeline_event.html', context)

def reports(request):
    data = generate_dashboard()
    context = {'type':'view', 'data':data}
    return render(request, 'viewer/reports.html', context)

def events(request):
    data = generate_dashboard()
    context = {'type':'view', 'data':data}
    return render(request, 'viewer/calendar.html', context)

def event(request, eid):
    data = get_object_or_404(Event, pk=eid)
    context = {'type':'event', 'data':data}
    return render(request, 'viewer/event.html', context)

def eventjson(request):
    dss = request.GET.get('start', '')
    dse = request.GET.get('end', '')
    dts = dateutil.parser.parse(dss)
    dte = dateutil.parser.parse(dse)
    ret = []
    for event in Event.objects.filter(end_time__gte=dts).filter(start_time__lte=dte):
        item = {}
        item['id'] = event.pk
        item['url'] = "#event_" + str(event.pk)
        item['title'] = event.caption
        item['start'] = event.start_time.isoformat()
        item['end'] = event.end_time.isoformat()
        item['backgroundColor'] = 'white'
        item['textColor'] = 'black'
        if event.type == 'journey':
            item['backgroundColor'] = 'green'
            item['textColor'] = 'white'
        if event.type == 'sleepover':
            item['backgroundColor'] = 'black'
            item['textColor'] = 'white'
        if event.type == 'photo':
            item['backgroundColor'] = 'orange'
            item['textColor'] = 'white'
        if event.type == 'loc_prox':
            item['backgroundColor'] = '#0073b7'
            item['textColor'] = 'white'
        ret.append(item)
    response = HttpResponse(json.dumps(ret), content_type='application/json')
    return response

def places(request):
    data = Location.objects.annotate(num_events=Count('events')).order_by('-num_events')
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            form.save()
            id = form.cleaned_data['uid']
            return HttpResponseRedirect('./#place_' + str(id))
        else:
            raise Http404("Error in POST input")
    else:
        form = LocationForm()
    context = {'type':'place', 'data':data, 'form':form}
    return render(request, 'viewer/places.html', context)

def place(request, uid):
    data = get_object_or_404(Location, uid=uid)
    context = {'type':'place', 'data':data}
    return render(request, 'viewer/place.html', context)

def people(request):
    data = Person.objects.annotate(num_events=Count('event')).order_by('-num_events')
    context = {'type':'person', 'data':data}
    return render(request, 'viewer/people.html', context)

def person(request, uid):
    data = get_object_or_404(Person, uid=uid)
    context = {'type':'person', 'data':data}
    return render(request, 'viewer/person.html', context)

def person_photo(request, uid):
    data = get_object_or_404(Person, uid=uid)
    im = data.photo()
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response

def place_photo(request, uid):
    data = get_object_or_404(Location, uid=uid)
    im = data.photo()
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response

def photo_thumbnail(request, uid):
    data = get_object_or_404(Photo, pk=uid)
    im = data.thumbnail(200)
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response

def person_thumbnail(request, uid):
    data = get_object_or_404(Person, uid=uid)
    im = data.thumbnail(100)
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response

def place_thumbnail(request, uid):
    data = get_object_or_404(Location, uid=uid)
    im = data.thumbnail(100)
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response
