from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from viewer.models import UserProfile
from viewer.forms import UserForm

import logging
logger = logging.getLogger(__name__)

def user_profile(request):
	context = {'user': request.user, 'form': UserForm(instance=request.user.profile)}
	ret = render(request, 'viewer/pages/profile.html', context)
	return ret

def user_thumbnail(request, username):
	data = get_object_or_404(User, username=username)
	im = data.profile.thumbnail(200)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response
