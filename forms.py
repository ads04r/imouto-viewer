from django.forms import ModelForm
from viewer.models import Location

class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time']
