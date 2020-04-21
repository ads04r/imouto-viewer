from django.forms import ModelForm, ImageField
from viewer.models import Location, Event
from django.db.models import Sum, Count
import datetime, pytz

class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time']

class QuickEventForm(ModelForm):
    class Meta:
        model = Event
        fields = ['caption', 'type', 'description']

class EventForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        self.fields['location'].queryset = Location.objects.exclude(creation_time__gt=now).exclude(destruction_time__lt=now).annotate(num_events=Count('events')).order_by('-num_events')
    class Meta:
        model = Event
        fields = ['caption', 'type', 'description', 'start_time', 'end_time', 'location']
