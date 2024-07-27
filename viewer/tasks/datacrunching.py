from background_task import background

from viewer.models import Event, EventSimilarity, Photo
from viewer.functions.geo import journey_similarity
from django.conf import settings

import logging, cv2
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
		diff = journey_similarity(e1, e2)

		try:
			es = EventSimilarity(event1=e1, event2=e2, diff_value=diff)
			es.save()
			print(es)
		except:
			pass

		try:
			es = EventSimilarity(event1=e2, event2=e1, diff_value=diff)
			es.save()
			print(es)
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

