import datetime, pytz
from haystack import indexes
from .models import *

class EventIndex(indexes.SearchIndex, indexes.Indexable):

	text = indexes.CharField(document=True, use_template=True)
	start_time = indexes.DateTimeField(model_attr='start_time')
	end_time = indexes.DateTimeField(model_attr='end_time')

	def get_model(self):
		return Event

	def get_updated_field(self):
		return 'start_time'


#    start_time = models.DateTimeField()
#    end_time = models.DateTimeField()
#    type = models.SlugField(max_length=32)
#    caption = models.CharField(max_length=255, default='', blank=True)
#    description = models.TextField(default='', blank=True)
#    people = models.ManyToManyField(Person, through='PersonEvent')
#    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
#    geo = models.TextField(default='', blank=True)

