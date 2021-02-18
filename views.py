from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from background_task.models import Task
from haystack.query import SearchQuerySet
import datetime, pytz, dateutil.parser, json, tzlocal

from .tasks import *
from .models import *
from .forms import *
from .functions import *

def index(request):
    context = {'type':'index', 'data':[]}
    return render(request, 'viewer/index.html', context)

def dashboard(request):
    key = 'dashboard'
    ret = cache.get(key)
    if ret is None:
        data = generate_dashboard()
        context = {'type':'view', 'data':data}
        ret = render(request, 'viewer/dashboard.html', context)
        cache.set(key, ret, timeout=86400)
    return ret

def onthisday(request):
    key = 'onthisday_' + datetime.date.today().strftime("%Y%m%d")
    data = cache.get(key)
    if data is None:
        data = generate_onthisday()
        cache.set(key, data, timeout=86400)
    context = {'type':'view', 'data':data}
    ret = render(request, 'viewer/onthisday.html', context)
    return ret

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
    dtq = datetime.datetime(dsyear, dsmonth, dsday, 0, 0, 0, tzinfo=tzlocal.get_localzone())
    events = get_timeline_events(dtq)

    dtq = events[0].start_time
    dtn = dtq - datetime.timedelta(days=1)
    dsn = dtn.strftime("%Y%m%d")

    context = {'type':'view', 'data':{'label': dtq.strftime("%A %-d %B"), 'next': dsn, 'events': events}}
    return render(request, 'viewer/timeline_event.html', context)

def reports(request):
    if request.method == 'POST':
        form = CreateReportForm(request.POST)
        if form.is_valid():
            year = int(request.POST['year'])
            dss = datetime.datetime(year, 1, 1, 0, 0, 0, tzinfo=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
            dse = datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
            title = str(request.POST['label'])
            style = str(request.POST['style'])
            if 'moonshine_url' in request.POST:
                generate_report(title, dss, dse, 'year', style, str(request.POST['moonshine_url']))
            else:
                generate_report(title, dss, dse, 'year', style)
            return HttpResponseRedirect('./#reports')
        else:
            raise Http404(form.errors)

    form = CreateReportForm()
    data = LifeReport.objects.all().order_by('-modified_date')
    context = {'type':'view', 'data':data, 'form': form, 'settings': {}, 'years': []}
    y1 = Event.objects.all().order_by('start_time')[0].start_time.year + 1
    y2 = Event.objects.all().order_by('-start_time')[0].start_time.year - 1
    for y in range(y2, y1 - 1, -1):
        context['years'].append(y)
    if hasattr(settings, 'MOONSHINE_URL'):
        if settings.MOONSHINE_URL != '':
            context['settings']['moonshine_url'] = settings.MOONSHINE_URL
    return render(request, 'viewer/reports.html', context)

def events(request):
    if request.method == 'POST':
        cache.delete('dashboard')
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            if event.type == 'journey':
                event.geo = getgeoline(event.start_time, event.end_time, request.META['HTTP_HOST'])
                #event.elevation = getelevation(event.start_time, event.end_time, request.META['HTTP_HOST'])
                event.save()

            return HttpResponseRedirect('./#event_' + str(event.id))
        else:
            raise Http404(form.errors)

    data = {}
    data['event'] = Event.objects.filter(type='event').order_by('-start_time')[0:10]
    data['journey'] = Event.objects.filter(type='journey').order_by('-start_time')[0:10]
    data['photo'] = Event.objects.filter(type='photo').exclude(caption='Photos').order_by('-start_time')[0:10]
    data['life'] = Event.objects.filter(type='life_event').order_by('-start_time')
    form = EventForm()
    context = {'type':'view', 'data':data, 'form':form}
    return render(request, 'viewer/calendar.html', context)

def event(request, eid):

    cache_key = 'event_' + str(eid)

    if request.method == 'POST':

        cache.delete('dashboard')
        data = get_object_or_404(Event, pk=eid)

        form = EventForm(request.POST, instance=data)
        if form.is_valid():
            event = form.save()
            if event.type == 'journey':
                event.geo = getgeoline(event.start_time, event.end_time, request.META['HTTP_HOST'])
                #event.elevation = getelevation(event.start_time, event.end_time, request.META['HTTP_HOST'])
                event.save()
            cache.set(cache_key, data, 86400)
            return HttpResponseRedirect('../#event_' + str(eid))
        else:
            form = QuickEventForm(request.POST, instance=data)
            if form.is_valid():
                form.save()
                cache.set(cache_key, data, 86400)
                return HttpResponseRedirect('../#event_' + str(eid))
            else:
                raise Http404(form.errors)

    data = cache.get(cache_key)
    if data is None:
        data = get_object_or_404(Event, pk=eid)
        cache.set(cache_key, data, 86400)

    form = EventForm(instance=data)
    context = {'type':'event', 'data':data, 'form':form, 'people':Person.objects.all()}
    template = 'viewer/event.html'
    if data.type=='life_event':
        template = 'viewer/lifeevent.html'
    return render(request, template, context)

@csrf_exempt
def eventdelete(request, eid):
    cache.delete('dashboard')
    if request.method != 'POST':
        raise Http404()
    data = get_object_or_404(Event, pk=eid)
    ret = data.delete()
    response = HttpResponse(json.dumps(ret), content_type='application/json')
    return response

@csrf_exempt
def eventpeople(request):
    cache.delete('dashboard')
    if request.method != 'POST':
        raise Http404()
    eid = request.POST['id']
    pids = request.POST['people'].split('|')
    data = get_object_or_404(Event, pk=eid)
    people = []
    for pid in pids:
        people.append(get_object_or_404(Person, uid=pid))
    data.people.clear()
    for person in people:
        data.people.add(person)
    return HttpResponseRedirect('./#event_' + str(data.id))

def eventjson(request):
    dss = request.GET.get('start', '')
    dse = request.GET.get('end', '')
    dts = dateutil.parser.parse(dss)
    dte = dateutil.parser.parse(dse)
    tz = tzlocal.get_localzone()
    ret = []
    for event in Event.objects.filter(end_time__gte=dts).filter(start_time__lte=dte):
        item = {}
        item['id'] = event.pk
        item['url'] = "#event_" + str(event.pk)
        item['title'] = event.caption
        item['start'] = event.start_time.astimezone(tz).isoformat()
        item['end'] = event.end_time.astimezone(tz).isoformat()
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
        cache.delete('dashboard')
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

def report(request, id):
    data = get_object_or_404(LifeReport, id=id)
    context = {'type':'report', 'data':data}
    return render(request, 'viewer/report.html', context)

def report_pdf(request, id):
    data = get_object_or_404(LifeReport, id=id)
    pdf = open(data.pdf.path, 'rb')
    response = HttpResponse(content=pdf)
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = 'attachment; filename="%s.pdf"' % str(data)
    return response

def report_words(request, id):
    data = get_object_or_404(LifeReport, id=id)
    txt = data.words()
    response = HttpResponse(content=txt, content_type='text/plain')
    return response

def report_wordcloud(request, id):
    data = get_object_or_404(LifeReport, id=id)
    im = data.wordcloud()
    response = HttpResponse(content_type='image/png')
    im.save(response, "PNG")
    return response

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

@csrf_exempt
def search(request):
    if request.method != 'POST':
        raise Http404()
    data = json.loads(request.body)
    query = data['query']
    ret = []

    cache_key = 'search_' + query
    sq = cache.get(cache_key)
    if sq is None:
        sq = SearchQuerySet().filter(content=query)
        cache.set(cache_key, sq, 86400)

    for searchresult in sq:
        event = searchresult.object
        description = event.description[0:50]
        if len(description) == 50:
            description = description[0:(description.rfind(' '))]
            if len(description) > 0:
                description = description + ' ...'
        if description == '':
            description = event.start_time.strftime("%a %-d %b %Y")
        item = {'label': event.caption, 'id': event.id, 'description': description, 'date': event.start_time.strftime("%A %-d %B"), 'type': event.type, 'link': 'event_' + str(event.id)}
        ret.append(item)
    response = HttpResponse(json.dumps(ret), content_type='application/json')
    return response
