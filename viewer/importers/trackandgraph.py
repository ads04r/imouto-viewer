from django.conf import settings
from viewer.functions.trackandgraph import read_trackandgraph_file
from viewer.models import Year, YearProperty
import datetime, pytz

import logging
logger = logging.getLogger(__name__)

def import_trackandgraph(path):

	for year in Year.objects.order_by('year'):
		dts = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 1, 1, 0, 0, 0))
		dte = pytz.timezone(settings.TIME_ZONE).localize(datetime.datetime(year.year, 12, 31, 23, 59, 59))
		for item in read_trackandgraph_file(path, date_from=dts, date_to=dte):
			category = item['category'].lower()
			label = item['label']
			description = item['description']
			value = int(item['total'])
			year.properties.filter(category__iexact=category, key__iexact=label.lower()).delete()
			prop = YearProperty(year=year, category=category, key=label, value=str(value), description=description)
			prop.save()
