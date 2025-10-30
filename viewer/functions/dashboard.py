from django.contrib.auth.models import User
from viewer.models import Photo, Event, EventWorkoutCategory, EventTag, PersonProperty, DataReading, RemoteInteraction, create_or_get_day, create_or_get_month
import datetime, pytz

class Dashboard():

	def __init__(self, username):

		self.user = User.objects.get(username=username)
		self.last_event = Event.objects.filter(user=self.user).order_by('-start_time')[0].start_time

	def tags(self):

		tags = []
		for tag in EventTag.objects.filter(events__user=self.user, events__end_time__gte=(self.last_event - datetime.timedelta(days=7)), events__start_time__lte=self.last_event).distinct():
			id = str(tag.id)
			if id == '':
				continue
			tags.append({'id': id, 'colour': str(tag.colour)})
		return tags

	def month(self):

		y = int(datetime.datetime.now().year)
		m = int(datetime.datetime.now().month)
		return create_or_get_month(user=self.user, year=y, month=m)

	def exercise(self):

		workouts = []
		workout_total = 0
		dts = self.last_event - datetime.timedelta(days=7)
		dte = self.last_event
		for category in EventWorkoutCategory.objects.filter(user=self.user):
			v = 0.0
			for event in Event.objects.filter(user=self.user, end_time__gte=dts, start_time__lte=dte, workout_categories=category):
				v = v + event.distance()
			if v > 0:
				workouts.append({'id': category.pk, 'label': str(category), 'distance': int(v)})
				workout_total = workout_total + int(v)
		for i in range(0, len(workouts)):
			workouts[i]['prc'] = int(float(workouts[i]['distance']) / float(workout_total))
		return workouts

	def birthdays(self):

		birthdays = []
		dtd = datetime.datetime.now().date()
		for pp in PersonProperty.objects.filter(person__user=self.user, key='birthday'):
			if not(pp.person.significant):
				continue
			dtp = pp.person.next_birthday
			if dtp is None:
				ttb = 365
			else:
				ttb = (dtp - dtd).days
			if ttb <= 14:
				person_age = pp.person.age
				if not(person_age is None):
					person_age = person_age + 1
				birthdays.append([pp.person, dtp, person_age])
		birthdays = sorted(birthdays, key=lambda p: p[1])

		return birthdays

	def locations(self):

		locationdata = []
		for event in Event.objects.filter(user=self.user, start_time__gte=(self.last_event - datetime.timedelta(days=7))):
			location = event.location
			if location in locationdata:
				continue
			if location is None:
				continue
			if location.label == 'Home':
				continue
			locationdata.append(location)
		if len(locationdata) == 0:
			for event in Event.objects.filter(user=self.user, start_time__gte=(self.last_event - datetime.timedelta(days=7))):
				location = event.location
				if location in locationdata:
					continue
				if location is None:
					continue
				locationdata.append(location)

		return locationdata

	def stats(self):

		stats = {}
		now = pytz.utc.localize(datetime.datetime.utcnow())

		stats['Messages'] = RemoteInteraction.objects.filter(user=self.user, type='sms', time__gte=(self.last_event - datetime.timedelta(days=7))).count()
		stats['Phone Calls'] = RemoteInteraction.objects.filter(user=self.user, type='phone-call', time__gte=(self.last_event - datetime.timedelta(days=7))).count()

		weights = DataReading.objects.filter(user=self.user, type='weight', start_time__gte=(self.last_event - datetime.timedelta(days=7)))
		if weights.count() > 0:
			total_weight = 0.0
			for weight in weights:
				total_weight = total_weight + (float(weight.value) / 1000)
			stats['Average Weight'] = (float(int((total_weight / float(weights.count())) * 100)) / 100)

		stats['Photos'] = Photo.objects.filter(user=self.user, time__gte=(self.last_event - datetime.timedelta(days=7))).count()

		return stats

	def feed(self):

		ret = []
		for i in range(0, 7):
			dt = self.last_event.date() - datetime.timedelta(days=i)
			day = create_or_get_day(self.user, dt)
			if day is None:
				continue
			item = {"label": str(day), "events": [], "people": [], "places": []}
			for event in day.events.exclude(location__pk=self.user.profile.home_location).order_by('start_time'):
				if event.length < 300:
					continue
				item['events'].append(event)
			item['people'] = list(day.people.filter(significant=True))
			ret.append(item)
		return ret
