from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.contrib.staticfiles import finders
from viewer.functions.file_uploads import user_profile_image_upload_location
from PIL import Image
import datetime, os

def create_new_userprofile():
	ret = {}
	return ret

def create_new_dashboard():
	return [["calendar", "tags", "status", "exercise", "locations", "sleep"], ["birthdays", "feed"]]

class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	date_of_birth = models.DateField(null=True, blank=True)
	home_location = models.IntegerField(default=0)
	image = models.ImageField(blank=True, null=True, upload_to=user_profile_image_upload_location)
	rdf_namespace = models.URLField(null=True, blank=True)
	settings = models.JSONField(default=create_new_userprofile, encoder=DjangoJSONEncoder)
	dashboard = models.JSONField(default=create_new_dashboard, encoder=DjangoJSONEncoder)
	@property
	def dashboard_column_width(self):
		if len(self.dashboard) == 0:
			return 0
		return int(12 / len(self.dashboard))
	def thumbnail(self, size):
		try:
			im = Image.open(self.image.path)
		except:
			unknown = finders.find('viewer/graphics/unknown_person.jpg')
			if os.path.exists(unknown):
				im = Image.open(unknown)
			else:
				return None
		bbox = im.getbbox()
		w = bbox[2]
		h = bbox[3]
		if h > w:
			ret = im.crop((0, 0, w, w))
		else:
			x = int((w - h) / 2)
			ret = im.crop((x, 0, x + h, h))
		ret = ret.resize((size, size), 1)
		return ret
	@cached_property
	def age(self):
		today = datetime.datetime.now().date()
		birth_year = self.date_of_birth.year
		birthday_this_year = datetime.date(today.year, self.date_of_birth.month, self.date_of_birth.day)
		if birthday_this_year < today:
			return now.year - birth_year
		return (today.year - birth_year) - 1
	def __str__(self):
		return str(self.user)

@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)
	instance.profile.save()
