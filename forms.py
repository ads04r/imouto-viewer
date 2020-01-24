from django.forms import ModelForm, ImageField
from viewer.models import Location

class LocationForm(ModelForm):
    #uploaded_image = ImageField(required=False)
    class Meta:
        model = Location
        fields = ['uid', 'label', 'full_label', 'address', 'phone', 'description', 'lat', 'lon', 'url', 'wikipedia', 'image', 'creation_time', 'destruction_time']
