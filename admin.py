from django.contrib import admin
from .models import *

admin.site.register(Event)
admin.site.register(Person)
admin.site.register(Location)
admin.site.register(Photo)
admin.site.register(DataReading)
admin.site.register(RemoteInteraction)

