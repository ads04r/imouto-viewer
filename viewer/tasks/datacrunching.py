from background_task import background

from viewer.models import Event, EventSimilarity, Photo
from viewer.functions.geo import journey_similarity
from django.conf import settings
from geopy import distance

import logging, cv2, json
logger = logging.getLogger(__name__)

@background(schedule=0, queue='datacrunching')
def count_photo_faces(photo_id):

	if not hasattr(settings, "FACE_DETECTOR"):
		return # If there is no face detector configured, this task cannot function.
	logger.info("Task count_photo_faces beginning")

	photo = Photo.objects.get(id=photo_id)
	logger.debug("Working with file " + str(photo.file.path))
	face_cascade = cv2.CascadeClassifier(settings.FACE_DETECTOR)
	img = cv2.imread(photo.file.path)
	grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	faces = face_cascade.detectMultiScale(grey, 1.3, 5)
	face_count = len(faces)
	if photo.face_count == face_count:
		return
	photo.face_count = face_count
	photo.save(update_fields=['face_count'])

@background(schedule=0, queue='datacrunching')
def count_event_faces(event_id):

	if not hasattr(settings, "FACE_DETECTOR"):
		return # If there is no face detector configured, this task cannot function.
	logger.info("Task count_event_faces beginning")

	try:
		event = Event.objects.get(id=event_id)
	except:
		return # The event has been deleted
	logger.debug("Working with event " + str(event))
	face_cascade = cv2.CascadeClassifier(settings.FACE_DETECTOR)
	for photo in event.photos():
		logger.debug(" ... " + str(photo.file.path))
		try:
			img = cv2.imread(photo.file.path)
			grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
			faces = face_cascade.detectMultiScale(grey, 1.3, 5)
		except:
			faces = []
		face_count = len(faces)
		if photo.face_count == face_count:
			continue
		photo.face_count = face_count
		photo.save(update_fields=['face_count'])

@background(schedule=0, queue='datacrunching')
def regenerate_similar_events(event_id):

	logger.info("Task regenerate_similar_events beginning")

	e1 = Event.objects.get(id=event_id)
	logger.debug("Working with event " + str(e1))
	EventSimilarity.objects.filter(event1=e1).delete()
	EventSimilarity.objects.filter(event2=e1).delete()
	events = Event.objects.filter(type='journey')
	for e2 in events:
		if e1 == e2:
			continue
		dist1 = e1.distance()
		dist2 = e2.distance()
		data1 = json.loads(e1.geo)
		data2 = json.loads(e2.geo)
		route_diff = journey_similarity(e1, e2)
		if dist1 > dist2:
			if dist2 == 0.0:
				length_diff = dist1
			else:
				length_diff = dist1 / dist2
		else:
			if dist1 == 0.0:
				length_diff = dist2
			else:
				length_diff = dist2 / dist1
		position_diff = 100.0
		if (('bbox' in data1) & ('bbox' in data2)):
			avglat1 = data1['bbox'][3] + ((data1['bbox'][1] - data1['bbox'][3]) / 2)
			avglat2 = data2['bbox'][3] + ((data2['bbox'][1] - data2['bbox'][3]) / 2)
			avglon1 = data1['bbox'][0] + ((data1['bbox'][2] - data1['bbox'][0]) / 2)
			avglon2 = data2['bbox'][0] + ((data2['bbox'][2] - data2['bbox'][0]) / 2)
			position_diff = distance.distance((avglat1, avglon1), (avglat2, avglon2)).km

		try:
			es = EventSimilarity(event1=e1, event2=e2, route_diff=route_diff, length_diff=length_diff, position_diff=position_diff)
			es.save()
		except:
			pass

		try:
			es = EventSimilarity(event1=e2, event2=e1, route_diff=route_diff, length_diff=length_diff, position_diff=position_diff)
			es.save()
		except:
			pass

@background(schedule=0, queue='datacrunching')
def generate_similar_events(max_events=10):

	logger.info("Task generate_similar_events beginning")

	events = Event.objects.filter(similar_from=None, similar_to=None, type='journey')[0:max_events]
	if events.count() == 0:
		events = Event.objects.filter(type='journey').order_by('updated_time')[0:max_events]
	for e1 in events:
		regenerate_similar_events(e1.pk)

