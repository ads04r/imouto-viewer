from django import template
import datetime
register = template.Library()
@register.filter(name='time_delta')
def time_delta(value, f):
	dt_epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
	dt = dt_epoch + value
	return dt.strftime(f)
