from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('script/imouto.js', views.script),
    path('stats.html', views.dashboard),
    path('onthisday.html', views.onthisday),
    path('upload.html', views.importer),
    path('timeline.html', views.timeline),
    path('timeline/<ds>.html', views.timelineitem),
    path('reports.html', views.reports),
    path('reports/<id>.html', views.report),
    path('reports/<id>.pdf', views.report_pdf),
    path('reports/<id>.txt', views.report_words),
    path('reports/<id>.png', views.report_wordcloud),
    path('events.html', views.events),
    path('events.json', views.eventjson),
    path('events/<eid>.html', views.event),
    path('events/<eid>/delete', views.eventdelete),
    path('places.html', views.places),
    path('places/<uid>.html', views.place),
    path('places/<uid>_thumb.jpg', views.place_thumbnail),
    path('places/<uid>.jpg', views.place_photo),
    path('people.html', views.people),
    path('people/<uid>.html', views.person),
    path('people/<uid>_thumb.jpg', views.person_thumbnail),
    path('people/<uid>.jpg', views.person_photo),
    path('photo/<uid>_thumb.jpg', views.photo_thumbnail),
    path('photo/<uid>.jpg', views.photo_full),
    path('search.json', views.search),
    path('add-people-to-event', views.eventpeople),
]
