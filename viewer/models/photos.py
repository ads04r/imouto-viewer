from django.db import models

from viewer.models.core import Event, Photo

class PhotoCollage(models.Model):
	image = models.ImageField(blank=True, null=True) # , upload_to=photo_collage_upload_location)
	event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL, related_name='photo_collages')
	photos = models.ManyToManyField(Photo, related_name='photo_collages')
	def __str__(self):
		if self.event is None:
			return 'Unknown Event'
		else:
			return str(self.event.caption)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'photo collage'
		verbose_name_plural = 'photo collages'
