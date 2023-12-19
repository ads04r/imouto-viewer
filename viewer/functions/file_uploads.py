def user_thumbnail_upload_location(instance, filename):
	return 'people/' + str(instance.pk) + '/' + filename

def photo_thumbnail_upload_location(instance, filename):
	return 'thumbnails/' + str(instance.pk) + '.jpg'

def location_thumbnail_upload_location(instance, filename):
	return 'places/' + str(instance.uid) + '/' + filename

def report_pdf_upload_location(instance, filename):
	return 'reports/report_' + str(instance.id) + '.pdf'

def report_wordcloud_upload_location(instance, filename):
	return 'wordclouds/report_wc_' + str(instance.id) + '.png'

def report_graph_upload_location(instance, filename):
	return 'staticgraphs/report_graph_' + str(instance.id) + '.png'

def event_collage_upload_location(instance, filename):
	return 'events/event_collage_' + str(instance.id) + '.jpg'

def event_staticmap_upload_location(instance, filename):
	return 'events/event_staticmap_' + str(instance.id) + '.png'

def tag_staticmap_upload_location(instance, filename):
	return 'autotag/tag_staticmap_' + str(instance.pk) + '.png'

def year_wordcloud_upload_location(instance, filename):
	return 'wordclouds/year_wc_' + str(instance.year) + '.png'
