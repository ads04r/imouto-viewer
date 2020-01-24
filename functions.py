import datetime, pytz, json, random
from viewer.models import *
from django.db.models import Sum, Count

def generate_dashboard():

    stats = {}
    
    last_contact = RemoteInteraction.objects.all().order_by('-time')[0].time
    
    contactdata = []
    stats['messages'] = len(RemoteInteraction.objects.filter(time__gte=(last_contact - datetime.timedelta(days=7))))
    for i in RemoteInteraction.objects.filter(time__gte=(last_contact - datetime.timedelta(days=7))).values('address').annotate(messages=Count('address')).order_by('-messages'):
        address = i['address'].replace(' ', '')
        try:
            person = PersonProperty.objects.get(value=address).person
        except:
            person = None
        if(not(person is None)):
            item = {'person': person, 'address': address, 'messages': int(i['messages'])}
            contactdata.append(item)

    locationdata = []
    last_event = Event.objects.all().order_by('-start_time')[0].start_time
    for event in Event.objects.filter(start_time__gte=(last_event - datetime.timedelta(days=7))):
        location = event.location
        if location in locationdata:
            continue
        if location is None:
            continue
        locationdata.append(location)

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
    
    return {'stats': stats, 'steps': json.dumps(stepdata), 'sleep': json.dumps(sleepdata), 'contact': contactdata, 'places': locationdata, 'walks': walkdata}

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
