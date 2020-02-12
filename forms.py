from django.forms import ModelForm, ImageField
from viewer.models import Location, Event

class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time']

class QuickEventForm(ModelForm):
    class Meta:
        model = Event
        fields = ['caption', 'type', 'description']
