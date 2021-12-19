from django.forms import ModelForm, ImageField, TextInput, Textarea, Select
from viewer.models import Location, Event, LifeReport
from django.db.models import Sum, Count
import datetime, pytz

class LocationForm(ModelForm):
	class Meta:
		model = Location
		fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time', 'country']
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
			'creation_time': TextInput(attrs={'class': 'form-control'}),
			'destruction_time': TextInput(attrs={'class': 'form-control'}),
			'country': Select(attrs={'class': 'form-control'}),
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
		now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
		self.fields['location'].queryset = Location.objects.exclude(creation_time__gt=now).exclude(destruction_time__lt=now).annotate(num_events=Count('events')).order_by('-num_events')
	class Meta:
		model = Event
		fields = ['caption', 'type', 'description', 'start_time', 'end_time', 'location']
		widgets = {
			'caption': TextInput(attrs={'class': 'form-control'}),
			'type': TextInput(attrs={'class': 'form-control'}),
			'location': Select(attrs={'class': 'form-control'}),
			'description': Textarea(attrs={'class': 'form-control'}),
			'start_time': TextInput(attrs={'class': 'form-control'}),
			'end_time': TextInput(attrs={'class': 'form-control'}),
		}

class CreateReportForm(ModelForm):
	class Meta:
		model = LifeReport
		fields = ['label', 'style']
