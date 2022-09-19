from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('script/imouto.js', views.script),
    path('stats.html', views.dashboard),
    path('stats.json', views.dashboard_json),
    path('onthisday.html', views.onthisday),
    path('upload.html', views.importer),
    path('timeline.html', views.timeline),
    path('timeline/<ds>.html', views.timelineitem),
    path('reports.html', views.reports),
    path('reports.json', views.reports_json),
    path('report_queue.json', views.report_queue),
    path('reports/<id>.html', views.report),
    path('reports/<id>.json', views.report_json),
    path('reports/<id>.pdf', views.report_pdf),
    path('reports/<id>.txt', views.report_words),
    path('reports/<id>.png', views.report_wordcloud),
    path('reports/<rid>/delete', views.reportdelete),
    path('days/<ds>.html', views.day),
    path('days/<ds>/heart.json', views.day_heart),
    path('days/<ds>/sleep.json', views.day_sleep),
    path('days/<ds>/weight.json', views.day_weight),
    path('days/<ds>/people.json', views.day_people),
    path('days/<ds>/events.json', views.day_events),
    path('days/<ds>/locevents.json', views.day_locevents),
    path('tags.html', views.tags),
    path('tags/<id>.html', views.tag),
    path('events.html', views.events),
    path('events.json', views.eventjson),
    path('events/<eid>.html', views.event),
    path('events/<eid>.json', views.event_json),
    path('events/<eid>.jpg', views.event_collage),
    path('events/<eid>.png', views.event_staticmap),
    path('events/<eid>.gpx', views.event_gpx),
    path('events/<eid>/delete', views.eventdelete),
    path('places.html', views.places),
    path('places/<uid>.html', views.place),
    path('places/<uid>.json', views.place_json),
    path('places/<uid>_thumb.jpg', views.place_thumbnail),
    path('places/<uid>.jpg', views.place_photo),
    path('people.html', views.people),
    path('people/<uid>.html', views.person),
    path('people/<uid>.json', views.person_json),
    path('people/<uid>_thumb.jpg', views.person_thumbnail),
    path('people/<uid>.jpg', views.person_photo),
    path('photo/<uid>_thumb.jpg', views.photo_thumbnail),
    path('photo/<uid>.jpg', views.photo_full),
    path('photo/<uid>.json', views.photo_json),
    path('search.json', views.search),
    path('add-people-to-event', views.eventpeople),
    path('upload_file', views.upload_file),
    path('health/<pageid>.html', views.health),
    path('import', views.locman_import),
    path('process', views.locman_process),
]
