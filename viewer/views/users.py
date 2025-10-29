from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404

import logging
logger = logging.getLogger(__name__)

def user_thumbnail(request, username):
	data = get_object_or_404(User, username=username)
	im = data.profile.thumbnail(200)
	response = HttpResponse(content_type='image/jpeg')
	im.save(response, "JPEG")
	return response
