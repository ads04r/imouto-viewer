import datetime, time, pytz, json, random, urllib.request, re, sys
from viewer.models import *
from background_task.models import Task
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField, fields
from django.core.cache import cache
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

def get_report_queue():

    ret = []
    for task in Task.objects.filter(queue='reports').order_by('run_at'):
        item = {'id': task.task_hash, 'name': task.task_name, 'error': task.has_error(), 'running': False}
        if task.locked_by_pid_running():
            item['running'] = True
        params = json.loads(task.task_params)
        if ((item['name'] == 'viewer.tasks.generate_photo_collages') or (item['name'] == 'viewer.tasks.generate_staticmap')):
            try:
                event = Event.objects.get(id=params[0][0])
            except:
                event = None
            if not(event is None):
                item['event'] = {"id": event.id, "type": event.type, "caption": event.caption, "date": event.start_time.strftime("%Y-%m-%d %H:%I:%S %z")}
        if item['name'] == 'viewer.tasks.generate_report_pdf':
            try:
                report = LifeReport.objects.get(id=params[0][0])
            except:
                report = None
            if not(report is None):
                item['report'] = {"id": report.id, "year": report.year(), "label": report.label}
        if item['name'] == 'viewer.tasks.generate_report':
            item['report'] = {"id": 0, "year": params[0][1][0:4], "label": params[0][0]}

        ret.append(item)

    return ret

def bubble_event_people():

    for event in Event.objects.filter(type='life_event'):
        for e in event.subevents():
            for person in e.people.all():
                event.people.add(person)

def get_timeline_events(dt):

    dtq = dt
    events = []
    while len(events) == 0:
        for event in Event.objects.filter(start_time__gte=dtq, start_time__lt=(dtq + datetime.timedelta(hours=24))).order_by('-start_time'):
            if __display_timeline_event(event):
                events.append(event)
        dtq = dtq - datetime.timedelta(hours=24)
    return events

def get_heart_history(days):

    dte = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
    dts = dte - datetime.timedelta(days=days)
    data = DataReading.objects.filter(start_time__gte=dts, type='heart-rate').order_by('start_time')
    ret = []
    last = 0
    if data.count() > 0:
        last = int(time.mktime(data[0].start_time.timetuple()))
    for item in data:
        dt = int(time.mktime(item.start_time.timetuple()))
        ret.append([(dt - last), item.value])
    return ret

def get_heart_graph(dt):

    key = 'heartgraph_' + dt.strftime("%Y%m%d")
    ret = cache.get(key)
    if not(ret is None):
        return ret

    dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
    dte = dts + datetime.timedelta(days=1)
    last = None
    values = {}
    for item in DataReading.objects.filter(start_time__lt=dte, end_time__gte=dts, type='heart-rate').order_by('start_time'):
        dtx = int((item.start_time - dts).total_seconds() / 60)
        if dtx in values:
            if item.value < values[dtx]:
                continue
        values[dtx] = item.value
    ret = []
    for x in range(0, 1440):
        dtx = dts + datetime.timedelta(minutes=x)
        if x in values:
            y = values[x]
            if not(last is None):
                td = (dtx - last).total_seconds()
                if td > 600:
                    item = {'x': (last + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
                    ret.append(item)
                    item = {'x': (dtx - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S"), 'y': 0}
                    ret.append(item)
            item = {'x': dtx.strftime("%Y-%m-%dT%H:%M:%S"), 'y': y}
            last = dtx
            ret.append(item)

    cache.set(key, ret, timeout=86400)

    return(ret)

def get_heart_information(dt, graph=True):

    dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
    dte = dts + datetime.timedelta(days=1)
    dts_now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    dts_prev = dts - datetime.timedelta(days=1)
    dts_next = dts + datetime.timedelta(days=1)

    data = {'date': dts.strftime("%a %-d %b %Y"), 'heart': {}}

    data['prev'] = dts_prev.strftime("%Y%m%d")
    if dts_next < dts_now:
        data['next'] = dts_next.strftime("%Y%m%d")

    max_rate = 220 - int(((dts_now.date() - settings.USER_DATE_OF_BIRTH).days) / 365.25)
    zone_1 = int(float(max_rate) * 0.5)
    zone_2 = int(float(max_rate) * 0.7)

    data['heart']['abs_max_rate'] = max_rate

    max = 0
    zone = [0, 0, 0]
    for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte):
        if event.cached_health:
            health = event.health()
            if 'heartmax' in health:
                if health['heartmax'] > max:
                    max = health['heartmax']
            if 'heartzonetime' in health:
                zone[0] = zone[0] + health['heartzonetime'][0]
                zone[1] = zone[1] + health['heartzonetime'][1]
                zone[2] = zone[2] + health['heartzonetime'][2]
    if max > 0:
        total_heart_time = zone[0] + zone[1] + zone[2]
        if ((total_heart_time > 0) & (total_heart_time < 86400)):
            zone[0] = zone[0] + (86400 - total_heart_time)
        data['heart']['day_max_rate'] = max
        data['heart']['heartzonetime'] = zone
        if graph:
            data['heart']['graph'] = get_heart_graph(dt)
    else:
        del data['heart']

    return data

def get_sleep_history(days):

    dte = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(hour=0, minute=0, second=0)
    dts = dte - datetime.timedelta(days=days)
    data = DataReading.objects.filter(start_time__gte=dts, type='awake').order_by('start_time')
    ret = [[], []]
    for item in data:
        tts = item.start_time.astimezone(pytz.timezone(settings.TIME_ZONE))
        tte = item.end_time.astimezone(pytz.timezone(settings.TIME_ZONE))
        wake_secs = (tts - tts.replace(hour=0, minute=0, second=0)).total_seconds()
        sleep_secs = (tte - tts).total_seconds() + wake_secs
        if len(ret[0]) == 0:
            ret[0].append(wake_secs)
            ret[1].append(sleep_secs)
            continue
        if (ret[1][-1] + 3600) < wake_secs:
            ret[1][-1] = sleep_secs
        else:
            ret[0].append(wake_secs)
            ret[1].append(sleep_secs)
    return ret

def get_sleep_information(dt):

    dts = datetime.datetime(dt.year, dt.month, dt.day, 4, 0, 0, tzinfo=pytz.timezone(settings.TIME_ZONE))
    dte = datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=pytz.timezone(settings.TIME_ZONE))
    dts_now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    dts_prev = dts - datetime.timedelta(days=1)
    dts_next = dts + datetime.timedelta(days=1)

    expression = F('end_time') - F('start_time')
    wrapped_expression = ExpressionWrapper(expression, DurationField())

    data = {'date': dts.strftime("%a %-d %b %Y")}
    awake_set = DataReading.objects.filter(type='awake', start_time__gte=dts).annotate(length=wrapped_expression).filter(length__gte=datetime.timedelta(minutes=60)).order_by('start_time')
    event_count = awake_set.count()
    if event_count >= 1:
        awake = awake_set[0]
        data['wake_up'] = awake.start_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
        data['bedtime'] = awake.end_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
        data['wake_up_local'] = awake.start_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lstrip("0").lower()
        data['bedtime_local'] = awake.end_time.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lstrip("0").lower()
        data['length'] = awake.length.total_seconds()
        try:
            tomorrow = DataReading.objects.filter(type='awake', start_time__gt=dte).order_by('start_time')[0].start_time
            data['tomorrow'] = tomorrow.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")
        except IndexError:
            tomorrow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        if event_count >= 2:
            sleep_data = []
            for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=awake.start_time, end_time__lte=tomorrow).order_by('start_time'):
                sleep_data.append(sleep_info)
            if len(sleep_data) > 0:
                data['sleep'] = parse_sleep(sleep_data)
        else:
            sleep_data = []
            for sleep_info in DataReading.objects.filter(type='sleep', start_time__gt=awake.start_time).order_by('start_time'):
                sleep_data.append(sleep_info)
            if len(sleep_data) > 0:
                data['sleep'] = parse_sleep(sleep_data)
    data['prev'] = dts_prev.strftime("%Y%m%d")
    if dts_next < dts_now:
        data['next'] = dts_next.strftime("%Y%m%d")

    return data

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

def getelevation(dts, dte, address='127.0.0.1:8000'):

    id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
    url = "http://" + address + "/location-manager/elevation/" + id + "?format=json"
    data = []
    with urllib.request.urlopen(url) as h:
        for item in json.loads(h.read().decode()):
            data.append({'x': item[1], 'y': item[2]})
    if len(data) > 0:
        return json.dumps(data)
    return ""

def getspeed(dts, dte, address='127.0.0.1:8000'):

    id = dts.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S") + dte.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
    url = "http://" + address + "/location-manager/elevation/" + id + "?format=json"
    data = []
    last_dist = 0
    last_time = dts
    with urllib.request.urlopen(url) as h:
        for item in json.loads(h.read().decode()):
            dt = datetime.datetime.strptime(re.sub('\.[0-9]+', '', item[0]), "%Y-%m-%dT%H:%M:%S%z")
            time_diff = (dt - last_time).total_seconds()
            dist_diff = item[1] - last_dist
            speed = 0
            if time_diff > 0:
                speed = ((dist_diff / 1609.344) / (time_diff / 3600))
            data.append({'x': item[0], 'y': speed})
            last_time = dt
            last_dist = item[1]
    if len(data) > 0:
        return json.dumps(data)
    return ""

def generate_onthisday():

    ret = []

    for i in range(1, 20):

        offset = datetime.timedelta(hours=4)

        dt = datetime.datetime.now().replace(tzinfo=get_localzone())
        year = dt.year - i
        dt = dt.replace(year=year)
        dts = dt.replace(hour=0, minute=0, second=0) + offset
        dte = dt.replace(hour=23, minute=59, second=59) + offset

        events = []
        places = []
        people = []
        journeys = []
        for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte):
            for person in event.people.all():
                if not(person in people):
                    people.append(person)
            if not(event.location is None):
                if event.location.label != 'Home':
                    if not(event.location in places):
                        places.append(event.location)
            if event.type == 'journey':
                if ((event.distance() > 10) or (len(event.description) > 0)):
                    journeys.append(event)
                    continue
            if len(str(event.description)) > 0:
                events.append(event)
                continue
            if event.type == 'life_event' or event.type == 'event': # or event.type == 'photo':
                events.append(event)
        tweets = []
        for tweet in RemoteInteraction.objects.filter(type='microblogpost', address='', time__gte=dts, time__lte=dte):
            tweets.append(tweet)
        photos = []
        for photo in Photo.objects.filter(time__gte=dts, time__lte=dte):
            photos.append(photo)
            for person in photo.people.all():
                if not(person in people):
                    people.append(person)

        if len(events) > 0 or len(photos) > 0 or len(places) > 0 or len(journeys) > 0:
            item = {}
            item['year'] = dts.year
            item['id'] = "day_" + dts.strftime("%Y%m%d")
            if i == 1:
                item['label'] = 'Last year'
            else:
                item['label'] = str(i) + ' years ago'
            item['events'] = events
            item['photos'] = photos
            item['places'] = places
            item['people'] = people
            item['tweets'] = tweets
            item['journeys'] = journeys
            countries = []
            for loc in places:
                if loc.country in countries:
                    continue
                countries.append(loc.country)
            if len(countries) > 0:
                item['country'] = countries[0]

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
    user_heart_high = int((220.0 - user_age) * 0.7)

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

    tags = []
    for tag in EventTag.objects.filter(events__end_time__gte=(last_event - datetime.timedelta(days=7)), events__start_time__lte=last_event).distinct():
        id = str(tag.id)
        if id == '':
            continue
        tags.append({'id': id, 'colour': str(tag.colour)})

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
            total_weight = total_weight + (float(weight.value) / 1000)
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
        obj = DataReading.objects.filter(type='step-count').filter(start_time__gte=dt, end_time__lt=(dt + datetime.timedelta(days=1))).aggregate(Sum('value'))
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
    walk_dist = 0.0
    dt = (last_record - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC)
    for walk in DataReading.objects.filter(start_time__gte=dt, type='pebble-app-activity', value='5'):
        try:
            ev = Event.objects.get(start_time=walk.start_time, end_time=walk.end_time, type='journey')
        except:
            ev = None
        if ev is None:
            continue
        walk_dist = walk_dist + ev.distance()
    if walk_dist > 0:
        stats['walk_distance'] = float(int(walk_dist * 100)) / 100

    heartdata = []

    if DataReading.objects.filter(type='heart-rate', start_time__gte=(last_record - datetime.timedelta(days=7))).count() > 0:
        duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.BigIntegerField())

        for i in range(0, 7):
            dtbase = last_record - datetime.timedelta(days=(7 - i))
            info = get_heart_information(dtbase, False)
            try:
                zone = info['heart']['heartzonetime']
            except:
                zone = [0, 0, 0]

            item = {}
            item['label'] = dtbase.strftime("%a")
            item['value'] = [zone[1], zone[2]]
            item['link'] = "#day_" + dtbase.strftime("%Y%m%d")
            heartdata.append(item)

    sleepdata = []
    for i in range(0, 7):
        dtbase = last_record - datetime.timedelta(days=(7 - i))
        dt = datetime.datetime(dtbase.year, dtbase.month, dtbase.day, 16, 0, 0, tzinfo=dtbase.tzinfo)
        total_sleep = 0
        deep_sleep = 0
        obj = DataReading.objects.filter(type='sleep').filter(value=1).filter(start_time__gte=(dt - datetime.timedelta(days=1))).filter(end_time__lt=dt)
        for item in obj:
            total_sleep = total_sleep + ((item.end_time) - (item.start_time)).total_seconds()
        obj = DataReading.objects.filter(type='sleep').filter(value=2).filter(start_time__gte=(dt - datetime.timedelta(days=1))).filter(end_time__lt=dt)
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

    birthdays = []
    dtd = datetime.datetime.now().date()
    for person in Person.objects.exclude(birthday=None).order_by('birthday__month', 'birthday__day'):
        dtp = person.birthday.replace(year=dtd.year)
        if dtp < dtd:
            dtp = person.birthday.replace(year=(dtd.year + 1))
        ttb = (dtp - dtd).days
        if ttb <= 14:
            birthdays.append([person, dtp, (dtp.year - person.birthday.year)])

    ret = {'stats': stats, 'birthdays': birthdays, 'steps': json.dumps(stepdata), 'sleep': json.dumps(sleepdata), 'contact': contactdata, 'people': peopledata, 'places': locationdata, 'walks': walkdata}
    if len(tags) > 0:
        ret['tags'] = tags
    if len(heartdata) > 0:
        ret['heart'] = json.dumps(heartdata)
    return ret

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

def generate_location_events(minlength):

    url = settings.LOCATION_MANAGER_URL + '/process'
    r = urllib.request.urlopen(url)
    data = json.loads(r.read())
    dts = Event.objects.filter(type='loc_prox').exclude(caption='Home').order_by('-start_time')[0].start_time.replace(hour=0, minute=0, second=0)
    dte1 = datetime.datetime.fromtimestamp(int(data['stats']['last_calculated_positon'])).replace(tzinfo=pytz.UTC)
    dte2 = Event.objects.all().order_by('-end_time')[0].end_time
    if dte1 > dte2:
        dte = dte1
    else:
        dte = dte2
    min_duration = int(minlength)

    ret = []

    duration = int(((dte - dts).total_seconds()) / (60 * 60 * 24))
    mils = re.compile(r"\.([0-9]+)")

    for i in range(0, duration + 1):
        dt = dts + datetime.timedelta(days=i)
        dtt = dt + datetime.timedelta(days=1)
        url = settings.LOCATION_MANAGER_URL + "/route/" + dt.strftime("%Y%m%d") + '040000' + dtt.strftime("%Y%m%d") + "040000?format=json"
        data = []
        with urllib.request.urlopen(url) as h:
            data = json.loads(h.read().decode())
        if not('geo' in data):
            continue
        if not('bbox' in data['geo']):
            continue

        lat1 = data['geo']['bbox'][1]
        lat2 = data['geo']['bbox'][3]
        lon1 = data['geo']['bbox'][0]
        lon2 = data['geo']['bbox'][2]
        if lat1 > lat2:
            lat1 = data['geo']['bbox'][3]
            lat2 = data['geo']['bbox'][1]
        if lon1 > lon2:
            lon1 = data['geo']['bbox'][2]
            lon2 = data['geo']['bbox'][0]
        for location in Location.objects.filter(lon__gte=lon1, lon__lte=lon2, lat__gte=lat1, lat__lte=lat2):

            if not(location.destruction_time is None):
                if location.destruction_time < dt:
                    continue

            url = settings.LOCATION_MANAGER_URL + "/event/" + dt.strftime("%Y-%m-%d") + "/" + str(location.lat) + "/" + str(location.lon) + "?format=json"

            data = []
            try:
                with urllib.request.urlopen(url) as h:
                    data = json.loads(h.read().decode())
            except:
                sys.stderr.write("Reading " + url + " failed\n")
                data = []
            if len(data) == 0:
                continue
            for item in data:
                dtstart = datetime.datetime.strptime(mils.sub("", item['timestart']), "%Y-%m-%dT%H:%M:%S%z")
                dtend = datetime.datetime.strptime(mils.sub("", item['timeend']), "%Y-%m-%dT%H:%M:%S%z")
                dtlen = (dtend - dtstart).total_seconds()
                if dtlen < min_duration:
                    continue
                if location.label == 'Home':
                    continue
                if Event.objects.filter(start_time__lte=dtstart, end_time__gte=dtend).count() > 0:
                    continue
                if Event.objects.filter(start_time__lte=dtend, end_time__gte=dtstart).exclude(type='journey').count() > 0:
                    continue

                ev = Event(caption=location.label, location=location, start_time=dtstart, end_time=dtend, type='loc_prox')
                ret.append(ev)
                ev.save()

    return ret
