from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
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

def importer(request):
    context = {}
    return render(request, 'viewer/import.html', context)

def timeline(request):
    dt = Event.objects.order_by('-start_time')[0].start_time
    ds = dt.strftime("%Y%m%d")
    form = QuickEventForm()
    context = {'type':'view', 'data':{'current': ds}, 'form':form}
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
    data = {}
    data['event'] = Event.objects.filter(type='event').order_by('-start_time')[0:10]
    data['journey'] = Event.objects.filter(type='journey').order_by('-start_time')[0:10]
    data['photo'] = Event.objects.filter(type='photo').order_by('-start_time')[0:10]
    data['life'] = Event.objects.filter(type='life_event').order_by('-start_time')
    context = {'type':'view', 'data':data}
    return render(request, 'viewer/calendar.html', context)

def event(request, eid):
    data = get_object_or_404(Event, pk=eid)
    if request.method == 'POST':

        form = EventForm(request.POST, instance=data)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('../#event_' + str(eid))
        else:
            form = QuickEventForm(request.POST, instance=data)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('../#event_' + str(eid))
            else:
                raise Http404(form.errors)
    form = EventForm(instance=data)
    context = {'type':'event', 'data':data, 'form':form}
    template = 'viewer/event.html'
    if data.type=='life_event':
        template = 'viewer/lifeevent.html'
    return render(request, template, context)

@csrf_exempt
def eventdelete(request, eid):
    if request.method != 'POST':
        raise Http404()
    data = get_object_or_404(Event, pk=eid)
    ret = data.delete()
    response = HttpResponse(json.dumps(ret), content_type='application/json')
    return response

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
    data = {}
    datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=60)
    data['recent'] = Location.objects.filter(events__start_time__gte=datecutoff).annotate(num_events=Count('events')).order_by('-num_events')
    data['all'] = Location.objects.annotate(num_events=Count('events')).order_by('label')
    if request.method == 'POST':
        form = LocationForm(request.POST, request.FILES)
        if form.is_valid():
            #form.save()
            post = form.save(commit=False)
            id = form.cleaned_data['uid']
            if form.cleaned_data.get('uploaded_image'):
                #image = Image(title=post.full_label, description=post.description, image=request.FILES['uploaded_image'])
                #image.save()
                post.image = request.FILES['uploaded_image']
            post.save()
            return HttpResponseRedirect('./#place_' + str(id))
        else:
            raise Http404(form.errors)
    else:
        form = LocationForm()
    context = {'type':'place', 'data':data, 'form':form}
    return render(request, 'viewer/places.html', context)

def place(request, uid):
    data = get_object_or_404(Location, uid=uid)
    context = {'type':'place', 'data':data}
    return render(request, 'viewer/place.html', context)

def people(request):

    data = {}
    datecutoff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=365)
    data['recent'] = Person.objects.filter(event__start_time__gte=datecutoff).annotate(num_events=Count('event')).order_by('-num_events')
    data['all'] = Person.objects.annotate(num_events=Count('event')).order_by('given_name', 'family_name')
    context = {'type':'person', 'data':data}
    return render(request, 'viewer/people.html', context)

def person(request, uid):
    data = get_object_or_404(Person, uid=uid)
    context = {'type':'person', 'data':data, 'properties':explode_properties(data)}
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

def photo_full(request, uid):
    data = get_object_or_404(Photo, pk=uid)
    im = data.image()
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
