from django.contrib import admin
from .models import *

class PersonAdmin(admin.ModelAdmin):
	list_display = ['full_name', 'nickname', 'significant']
	ordering = ['-significant', 'family_name', 'given_name', 'nickname']

class LocationAdmin(admin.ModelAdmin):
	list_display = ['full_label', 'address', 'exists', 'city', 'country']

admin.site.register(Event)
admin.site.register(Person, PersonAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(DataReading)
admin.site.register(RemoteInteraction)
admin.site.register(EventTag)
admin.site.register(LocationCountry)
admin.site.register(LocationCity)

