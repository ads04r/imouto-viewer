import datetime, pytz, json, random, urllib.request
from .models import *
from django.db.models import Sum, Count, F, ExpressionWrapper, fields
from django.conf import settings
from geopy import distance
from tzlocal import get_localzone

def __display_timeline_event(event):

    if event.type == 'life_event':
        return False
    if event.description == '':
        if event.type == 'loc_prox':
            if event.location is None:
                return False
            if event.location.label == 'Home':
                if event.photos().count() == 0:
                    return False
        if event.type == 'journey':
            ddt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - datetime.timedelta(days=7)
            if event.end_time < ddt:
                if event.people.all().count() == 0:
                    if event.photos().count() == 0:
                        if (float(event.distance()) < 1):
                            return False
    return True

def get_timeline_events(dt):

    dtq = dt
    events = []
    while len(events) == 0:
        for event in Event.objects.filter(start_time__gte=dtq, start_time__lt=(dtq + datetime.timedelta(hours=24))).order_by('-start_time'):
            if __display_timeline_event(event):
                events.append(event)
        dtq = dtq - datetime.timedelta(hours=24)
    return events

def getgeoline(dts, dte, address='127.0.0.1:8000'):

    id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
    url = "http://" + address + "/location-manager/route/" + id + "?format=json"
    data = {}
    with urllib.request.urlopen(url) as h:
        data = json.loads(h.read().decode())
    if 'geo' in data:
        if 'geometry' in data['geo']:
            if 'coordinates' in data['geo']['geometry']:
                if len(data['geo']['geometry']['coordinates']) > 0:
                    return json.dumps(data['geo'])
    return ""

def generate_onthisday():

    ret = []

    for i in range(1, 20):

        dt = datetime.datetime.now().replace(tzinfo=get_localzone())
        year = dt.year - i
        dt = dt.replace(year=year)
        dts = dt.replace(hour=0, minute=0, second=0)
        dte = dt.replace(hour=23, minute=59, second=59)

        events = []
        places = []
        people = []
        for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte):
            for person in event.people.all():
                if not(person in people):
                    people.append(person)
            if not(event.location is None):
                if event.location.label != 'Home':
                    if not(event.location in places):
                        places.append(event.location)
            if len(str(event.description)) > 0:
                events.append(event)
                continue
            if event.type == 'life_event' or event.type == 'event': # or event.type == 'photo':
                events.append(event)
            if event.type == 'journey':
                if event.distance() > 10:
                    events.append(event)
        photos = []
        for photo in Photo.objects.filter(time__gte=dts, time__lte=dte):
            photos.append(photo)
            for person in photo.people.all():
                if not(person in people):
                    people.append(person)

        if len(events) > 0 or len(photos) > 0 or len(places) > 0:
            item = {}
            item['year'] = dts.year
            if i == 1:
                item['label'] = 'Last year'
            else:
                item['label'] = str(i) + ' years ago'
            item['events'] = events
            item['photos'] = photos
            item['places'] = places
            item['people'] = people
            ret.append(item)

    return ret

def generate_dashboard():

    stats = {}

    last_contact = RemoteInteraction.objects.all().order_by('-time')[0].time
    user_dob = settings.USER_DATE_OF_BIRTH
    user_home = settings.USER_HOME_LOCATION
    user_age = (datetime.datetime.now().date() - user_dob).total_seconds() / (86400 * 365.25)
    user_heart_max = int(220.0 - user_age)
    user_heart_low = int((220.0 - user_age) * 0.5)
    user_heart_medium = int((220.0 - user_age) * 0.7)
    user_heart_high = int((220.0 - user_age) * 0.85)

    contactdata = []
    stats['messages'] = len(RemoteInteraction.objects.filter(type='sms', time__gte=(last_contact - datetime.timedelta(days=7))))
    stats['phone_calls'] = len(RemoteInteraction.objects.filter(type='phone-call', time__gte=(last_contact - datetime.timedelta(days=7))))
    for i in RemoteInteraction.objects.filter(type='sms', time__gte=(last_contact - datetime.timedelta(days=7))).values('address').annotate(messages=Count('address')).order_by('-messages'):
        address = i['address'].replace(' ', '')
        try:
            person = PersonProperty.objects.get(value=address).person
        except:
            person = None
        if(not(person is None)):
            item = {'person': person, 'address': address, 'messages': int(i['messages'])}
            contactdata.append(item)

    last_event = Event.objects.all().order_by('-start_time')[0].start_time

    locationdata = []
    for event in Event.objects.filter(start_time__gte=(last_event - datetime.timedelta(days=7))):
        location = event.location
        if location in locationdata:
            continue
        if location is None:
            continue
        if location.label == 'Home':
            continue
        locationdata.append(location)
    if len(locationdata) == 0:
        for event in Event.objects.filter(start_time__gte=(last_event - datetime.timedelta(days=7))):
            location = event.location
            if location in locationdata:
                continue
            if location is None:
                continue
            locationdata.append(location)

    peopledata = []
    for event in Event.objects.filter(start_time__gte=(last_event - datetime.timedelta(days=7))):
        for person in event.people.all():
            if person in peopledata:
                continue
            peopledata.append(person)

    weights = DataReading.objects.filter(type='weight', start_time__gte=(last_event - datetime.timedelta(days=7)))
    if weights.count() > 0:
        total_weight = 0.0
        for weight in weights:
            total_weight = total_weight + float(weight.value)
        stats['weight'] = (float(int((total_weight / float(weights.count())) * 100)) / 100)

    stats['photos'] = 0
    try:
        last_photo = Photo.objects.all().order_by('-time')[0].time
        stats['photos'] = len(Photo.objects.filter(time__gte=(last_photo - datetime.timedelta(days=7))))
    except:
        stats['photos'] = 0

    stats['events'] = 0
    try:
        last_event = Event.objects.all().order_by('-start_time')[0].start_time
        stats['events'] = len(Event.objects.filter(start_time__gte=(last_event - datetime.timedelta(days=7))))
    except:
        stats['events'] = 0

    last_record = DataReading.objects.all().order_by('-end_time')[0].end_time
    
    stepdata = []
    total_steps = 0
    for i in range(0, 7):
        dtbase = last_record - datetime.timedelta(days=(7 - i))
        dt = datetime.datetime(dtbase.year, dtbase.month, dtbase.day, 0, 0, 0, tzinfo=dtbase.tzinfo)
        obj = DataReading.objects.filter(type='step-count').filter(start_time__gte=dt).filter(end_time__lt=(dt + datetime.timedelta(days=1))).aggregate(Sum('value'))
        try:
            steps = int(obj['value__sum'])
        except:
            steps = 0
        total_steps = total_steps + steps

        item = {}
        item['label'] = dt.strftime("%a")
        item['value'] = [steps]
        stepdata.append(item)
    stats['steps'] = total_steps

    heartdata = []
    duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.BigIntegerField())

    for i in range(0, 7):
        dtbase = last_record - datetime.timedelta(days=(7 - i))
        dt = datetime.datetime(dtbase.year, dtbase.month, dtbase.day, 0, 0, 0, tzinfo=dtbase.tzinfo)
        hrl = 0
        hrm = 0
        obj = DataReading.objects.filter(type='heart-rate').filter(value__gte=user_heart_low).filter(start_time__gte=dt, end_time__lt=(dt + datetime.timedelta(days=1)))
        for item in obj:
            if item.value >= user_heart_medium:
                hrm = hrm + ((item.end_time) - (item.start_time)).total_seconds()
            else:
                hrl = hrl + ((item.end_time) - (item.start_time)).total_seconds()

        item = {}
        item['label'] = dt.strftime("%a")
        item['value'] = [hrl, hrm]
        heartdata.append(item)

    sleepdata = []
    for i in range(0, 7):
        dtbase = last_record - datetime.timedelta(days=(7 - i))
        dt = datetime.datetime(dtbase.year, dtbase.month, dtbase.day, 16, 0, 0, tzinfo=dtbase.tzinfo)
        total_sleep = 0
        deep_sleep = 0
        obj = DataReading.objects.filter(type='pebble-app-activity').filter(value=1).filter(start_time__gte=(dt - datetime.timedelta(days=1))).filter(end_time__lt=dt)
        for item in obj:
            total_sleep = total_sleep + ((item.end_time) - (item.start_time)).total_seconds()
        obj = DataReading.objects.filter(type='pebble-app-activity').filter(value=2).filter(start_time__gte=(dt - datetime.timedelta(days=1))).filter(end_time__lt=dt)
        for item in obj:
            deep_sleep = deep_sleep + ((item.end_time) - (item.start_time)).total_seconds()
        light_sleep = total_sleep - deep_sleep

        item = {}
        item['label'] = dt.strftime("%a")
        item['value'] = [light_sleep, deep_sleep]
        sleepdata.append(item)
        
    walkdata = []
    for walk in DataReading.objects.filter(end_time__gte=(last_contact - datetime.timedelta(days=7))).filter(type='pebble-app-activity').filter(value=5):
        item = {}
        item['time'] = walk.end_time
        item['length'] = walk.length()
        m = int(item['length'] / 60)
        if m > 60:
            h = int(m / 60)
            m = m - (h * 60)
            if h == 1:
                item['friendly_length'] = str(h) + ' hour, ' + str(m) + ' minutes'
            else:
                item['friendly_length'] = str(h) + ' hours, ' + str(m) + ' minutes'
        else:
            item['friendly_length'] = str(m) + ' minutes'
        item['friendly_time'] = walk.start_time.strftime("%A") + ', ' + (walk.start_time.strftime("%I:%M%p").lower().lstrip('0'))
        walkdata.append(item)
    walkdata = sorted(walkdata, key=lambda item: item['length'], reverse=True)
    walkdata = walkdata[0:5]
    
    return {'stats': stats, 'steps': json.dumps(stepdata), 'sleep': json.dumps(sleepdata), 'heart': json.dumps(heartdata), 'contact': contactdata, 'people': peopledata, 'places': locationdata, 'walks': walkdata}

def explode_properties(person):
    prop = {}
    for k in person.get_properties():
        if k == 'mhb':
            continue
        if k == 'image':
            continue
        if k == 'livesat':
            continue
        if k == 'birthday':
            continue
        if k == 'hasface':
            continue
        v = person.get_property(k)
        prop[k] = v
    return prop

def nearest_location(lat, lon):
    now = datetime.datetime.now().replace(tzinfo=pytz.UTC)
    dist = 99999.9
    ret = None
    check = (lat, lon)
    for loc in Location.objects.exclude(destruction_time__lt=now).exclude(creation_time__gt=now):
        test = (loc.lat, loc.lon)
        newdist = distance.distance(test, check).km
        if newdist < dist:
            dist = newdist
            ret = loc
    return ret
