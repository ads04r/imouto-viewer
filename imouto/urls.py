from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from rest_framework import routers

from viewer import views

admin.site.site_header = 'Imouto Administration'
admin.site.site_title = 'Imouto Admin'

urlpatterns = [
    path('viewer/', include('viewer.urls')),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/viewer/', permanent=False)),
    path('favicon.ico', RedirectView.as_view(url='static/viewer/graphics/favicon.ico', permanent=True))
]
