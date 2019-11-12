from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
import datetime, pytz

from .models import *
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

def place(request, uid):
    data = get_object_or_404(Location, uid=uid)
    context = {'type':'place', 'data':data}
    return render(request, 'viewer/place.html', context)

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

def photo_thumbnail(request, uid):
    data = get_object_or_404(Photo, pk=uid)
    im = data.thumbnail(100)
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response

def person_thumbnail(request, uid):
    data = get_object_or_404(Person, uid=uid)
    im = data.thumbnail(100)
    response = HttpResponse(content_type='image/jpeg')
    im.save(response, "JPEG")
    return response
