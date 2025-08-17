from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import *

class UserProfileInline(admin.StackedInline):
	model = UserProfile
	can_delete = False
	verbose_name_plural = "user profiles"

class UserAdmin(BaseUserAdmin):
	inlines = [UserProfileInline]

class PersonAdmin(admin.ModelAdmin):
	list_display = ['name', 'full_name', 'significant']
	ordering = ['-significant', 'display_name', 'family_name', 'given_name']

class LocationAdmin(admin.ModelAdmin):
	list_display = ['label', 'address', 'exists', 'city', 'country']
	ordering = ['full_label']

class MessageAdmin(admin.ModelAdmin):
	list_display = ['time', 'type', 'person', 'incoming', 'message']
	ordering = ['-time']

class EventAdmin(admin.ModelAdmin):
	list_display = ['start_time', 'length_string', 'caption', 'type']
	ordering = ['-start_time']

class HistoricalEventAdmin(admin.ModelAdmin):
	list_display = ['date', 'category', 'description']
	ordering = ['-date']

class LifePeriodAdmin(admin.ModelAdmin):
	list_display = ['start_time', 'end_time', 'type', 'caption']
	ordering = ['-start_time']

class DataPointAdmin(admin.ModelAdmin):
	list_display = ['start_time', 'end_time', 'type', 'value']
	ordering = ['-start_time']

class WeatherPointAdmin(admin.ModelAdmin):
	list_display = ['time', 'location', 'description', 'temperature', 'wind_speed', 'humidity', 'visibility', 'wind_direction']
	ordering = ['-time']

class CountryAdmin(admin.ModelAdmin):
	list_display = ['label', 'a2']
	ordering = ['label']

class CityAdmin(admin.ModelAdmin):
	list_display = ['label', 'country']
	ordering = ['country', 'label']

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(Event, EventAdmin)
admin.site.register(LifePeriod, LifePeriodAdmin)
admin.site.register(HistoricalEvent, HistoricalEventAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(DataReading, DataPointAdmin)
admin.site.register(WeatherReading, WeatherPointAdmin)
admin.site.register(RemoteInteraction, MessageAdmin)
admin.site.register(LocationCountry, CountryAdmin)
admin.site.register(LocationCity, CityAdmin)

# TODO: Photo, GitCommit, SchemaOrgClass, WatchedDirectory, WeatherLocation(?)
