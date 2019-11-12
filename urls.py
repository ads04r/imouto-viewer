from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('stats.html', views.dashboard, name='dashboard'),
    path('timeline.html', views.timeline, name='timeline'),
    path('timeline/<ds>.html', views.timelineitem, name='timeline'),
    path('reports.html', views.reports, name='reports'),
    path('places/<uid>.html', views.place, name='place'),
    path('people/<uid>.html', views.person, name='person'),
    path('people/<uid>_thumb.jpg', views.person_thumbnail, name='person'),
    path('people/<uid>.jpg', views.person_photo, name='person'),
    path('photo/<uid>_thumb.jpg', views.photo_thumbnail, name='photo'),
]