from django.forms import ModelForm, ImageField, TextInput, Textarea, Select, DateInput, CheckboxInput, FileInput, URLInput, HiddenInput, CharField
from viewer.models import Location, Event, EventWorkoutCategory, LifePeriod, WatchedDirectory, Person, Questionnaire, QuestionnaireQuestion
from django.db.models import Sum, Count
from colorfield.fields import ColorWidget
import datetime, pytz

class LocationForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(LocationForm, self).__init__(*args, **kwargs)
		instance = getattr(self, 'instance', None)
		if instance and instance.pk:
			self.fields['uid'].disabled = True
	class Meta:
		model = Location
		fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time', 'parent']
		widgets = {
			'uid': TextInput(attrs={'class': 'form-control'}),
			'label': TextInput(attrs={'class': 'form-control'}),
			'full_label': TextInput(attrs={'class': 'form-control'}),
			'phone': TextInput(attrs={'class': 'form-control'}),
			'lat': TextInput(attrs={'class': 'form-control'}),
			'lon': TextInput(attrs={'class': 'form-control'}),
			'url': TextInput(attrs={'class': 'form-control'}),
			'wikipedia': TextInput(attrs={'class': 'form-control'}),
			'address': Textarea(attrs={'class': 'form-control'}),
			'description': Textarea(attrs={'class': 'form-control'}),
			'creation_time': TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD HH:MM:SS'}),
			'destruction_time': TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD HH:MM:SS'}),
			'parent': Select(attrs={'class': 'form-control'}),
		}

class PersonForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(PersonForm, self).__init__(*args, **kwargs)
		instance = getattr(self, 'instance', None)
		if instance and instance.pk:
			self.fields['uid'].disabled = True
	class Meta:
		model = Person
		fields = ['uid', 'given_name', 'family_name', 'nickname', 'image', 'significant', 'wikipedia']
		labels = {'significant': 'Important'}
		widgets = {
			'uid': TextInput(attrs={'class': 'form-control'}),
			'given_name': TextInput(attrs={'class': 'form-control'}),
			'family_name': TextInput(attrs={'class': 'form-control'}),
			'nickname': TextInput(attrs={'class': 'form-control'}),
			'wikipedia': URLInput(attrs={'class': 'form-control'}),
			'significant': CheckboxInput(attrs={'class': 'checkbox'}),
		}

class WorkoutCategoryForm(ModelForm):
	class Meta:
		model = EventWorkoutCategory
		fields = ['label', 'comment']
		widgets = {
			'label': TextInput(attrs={'class': 'form-control'}),
			'comment': Textarea(attrs={'class': 'form-control'}),
		}

class QuickEventForm(ModelForm):
	class Meta:
		model = Event
		fields = ['caption', 'type', 'description']
		widgets = {
			'caption': TextInput(attrs={'class': 'form-control'}),
			'type': TextInput(attrs={'class': 'form-control'}),
			'description': Textarea(attrs={'class': 'form-control'}),
		}

class EventForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		now = pytz.utc.localize(datetime.datetime.utcnow())
		self.fields['location'].queryset = Location.objects.exclude(creation_time__gt=now).exclude(destruction_time__lt=now).annotate(num_events=Count('events')).order_by('-num_events')
	class Meta:
		model = Event
		fields = ['caption', 'type', 'description', 'start_time', 'end_time', 'location']
		widgets = {
			'caption': TextInput(attrs={'class': 'form-control'}),
			'type': TextInput(attrs={'class': 'form-control'}),
			'location': Select(attrs={'class': 'form-control'}),
			'description': Textarea(attrs={'class': 'form-control'}),
			'start_time': TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD HH:MM:SS'}),
			'end_time': TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD HH:MM:SS'}),
		}

class LifePeriodForm(ModelForm):
	class Meta:
		model = LifePeriod
		fields = ['caption', 'type', 'description', 'colour', 'start_time', 'end_time']
		widgets = {
			'caption': TextInput(attrs={'class': 'form-control'}),
			'type': TextInput(attrs={'class': 'form-control'}),
			'description': Textarea(attrs={'class': 'form-control'}),
#			'colour': CharField(widget=ColorWidget),
			'start_time': DateInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
			'end_time': DateInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
		}

class WatchedDirectoryForm(ModelForm):
	def __init__(self, *args, **kwargs):
		super(WatchedDirectoryForm, self).__init__(*args, **kwargs)
		self.fields['importer'].label = "Contains file types"
	class Meta:
		model = WatchedDirectory
		fields = ['path', 'importer', 'recursive', 'check_interval', 'source', 'file_regex']
		widgets = {
			'path': TextInput(attrs={'class': 'form-control'}),
			'importer': Select(choices=(('fit', 'ANT-FIT files'), ('gpx', 'GPX files'), ('mood', 'Mini-Moods exported files'), ('jpg', 'Photos (JPG)')), attrs={'class': 'form-control'}),
			'check_interval': TextInput(attrs={'class': 'form-control'}),
			'source': TextInput(attrs={'class': 'form-control'}),
			'file_regex': TextInput(attrs={'class': 'form-control'}),
		}

class QuestionnaireForm(ModelForm):
	class Meta:
		model = Questionnaire
		fields = ['label', 'random_order']
		widgets = {
			'label': TextInput(attrs={'class': 'form-control'}),
			'random_order': CheckboxInput(attrs={'class': 'checkbox'}),
		}

class QuestionForm(ModelForm):
	class Meta:
		model = QuestionnaireQuestion
		fields = ['question', 'ordering']
		widgets = {
			'question': TextInput(attrs={'class': 'form-control'}),
			'ordering': HiddenInput(),
		}

