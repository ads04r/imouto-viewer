import datetime, pytz, json, requests
from background_task.models import Task
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField, fields
from django.conf import settings

from viewer.models import *

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

def generate_life_grid(start_date, weeks):

	life = []
	year = []
	year_birthday = settings.USER_DATE_OF_BIRTH
	for i in range(0, weeks):
		dts = start_date + datetime.timedelta(days=(7 * i))
		dte = dts + datetime.timedelta(days=6)
		if ((dts <= year_birthday) & (year_birthday <= dte)):
			year_birthday = year_birthday.replace(year=year_birthday.year + 1)
			if len(year) > 0:
				life.append(year)
				year = []
		dtts = datetime.datetime(dts.year, dts.month, dts.day, 0, 0, 0, tzinfo=pytz.UTC)
		dtte = datetime.datetime(dte.year, dte.month, dte.day, 23, 59, 59, tzinfo=pytz.UTC)
		item = {'start_time': dts, 'end_time': dte, 'events': Event.objects.filter(type='life_event', start_time__lte=dtte, end_time__gte=dtts), 'periods': LifePeriod.objects.filter(start_time__lte=dtte, end_time__gte=dtts)}
		year.append(item)
	if len(year) > 0:
		life.append(year)
	return life

def get_location_manager_report_queue():

	ret = []
	url = settings.LOCATION_MANAGER_URL + '/process'
	r = requests.get(url)
	data = json.loads(r.text)
	if 'tasks' in data:
		ret = ret + data['tasks']
	url = settings.LOCATION_MANAGER_URL + '/import'
	r = requests.get(url)
	data = json.loads(r.text)
	if 'tasks' in data:
		ret = ret + data['tasks']
	return ret

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
		if ((item['name'] == 'viewer.tasks.generate_report_pdf') or (item['name'] == 'viewer.tasks.generate_report_wordcloud')):
			try:
				report = LifeReport.objects.get(id=params[0][0])
			except:
				report = None
			if not(report is None):
				item['report'] = {"id": report.id, "year": report.year, "label": report.label}
		if item['name'] == 'viewer.tasks.generate_report':
			item['report'] = {"id": 0, "year": params[0][1], "label": params[0][0]}

		ret.append(item)

	return ret

def get_timeline_events(dt):

	dtq = dt
	events = []
	while len(events) == 0:
		for event in Event.objects.filter(start_time__gte=dtq, start_time__lt=(dtq + datetime.timedelta(hours=24))).order_by('-start_time'):
			if __display_timeline_event(event):
				events.append(event)
		dtq = dtq - datetime.timedelta(hours=24)
	return events

def generate_onthisday():

	ret = []

	for i in range(1, 20):

		offset = datetime.timedelta(hours=4)

		dt = datetime.datetime.now().replace(tzinfo=pytz.timezone(settings.TIME_ZONE))
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

	try:
		user_dob = settings.USER_DATE_OF_BIRTH
		user_age = (datetime.datetime.now().date() - user_dob).total_seconds() / (86400 * 365.25)
	except:
		return {'error': 'USER_DATE_OF_BIRTH must be set.'}
	try:
		last_contact = RemoteInteraction.objects.all().order_by('-time')[0].time
	except:
		try:
			last_contact = Event.objects.all().order_by('-end_time')[0].end_time
		except:
			return {}
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

	try:
		last_record = DataReading.objects.all().order_by('-end_time')[0].end_time
	except:
		last_record = last_contact

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
			day = create_or_get_day(dtbase.date())
			info = day.get_heart_information(False)
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
	for pp in PersonProperty.objects.filter(key='birthday'):
		dtp = pp.person.next_birthday
		ttb = (dtp - dtd).days
		if ttb <= 14:
			person_age = pp.person.age
			if not(person_age is None):
				person_age = person_age + 1
			birthdays.append([pp.person, dtp, person_age])
	birthdays = sorted(birthdays, key=lambda p: p[1])

	workouts = []
	dts = last_record - datetime.timedelta(days=7)
	dte = last_record
	for category in EventWorkoutCategory.objects.all():
		v = 0.0
		for event in Event.objects.filter(end_time__gte=dts, start_time__lte=dte, workout_categories=category):
			v = v + event.distance()
		if v > 0:
			workouts.append({'id': category.pk, 'label': str(category), 'distance': int(v)})

	ret = {'stats': stats, 'birthdays': birthdays, 'workouts': workouts, 'steps': json.dumps(stepdata), 'sleep': json.dumps(sleepdata), 'contact': contactdata, 'people': peopledata, 'places': locationdata, 'walks': walkdata}
	if len(tags) > 0:
		ret['tags'] = tags
	if len(heartdata) > 0:
		ret['heart'] = json.dumps(heartdata)
	return ret
