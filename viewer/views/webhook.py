from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt

from viewer.models import DataReading

import datetime, pytz, json

@csrf_exempt
def webhook(request, path=''):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])
	value = ''
	try:
		data = json.loads(request.body)
	except:
		data = {}
	if not(isinstance(data, dict)):
		data = {}
	if 'value' in data:
		value = data['value']
	type = path
	if len(path) > 32:
		type = path[0:32]
	if not(isinstance(value, (int, float))):
		value = None
	ret = ''
	if not(value is None):
		dt = pytz.utc.localize(datetime.datetime.utcnow())
		item = DataReading(start_time=dt, end_time=dt, type=type, value=value)
		item.save()
		ret = str(item.pk)
	response = HttpResponse(ret, content_type='text/plain')
	return response
