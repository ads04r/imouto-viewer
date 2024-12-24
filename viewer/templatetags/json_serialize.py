from django import template
from json import dumps

register = template.Library()

@register.filter(name='json_serialize')
def json_serialize(value):
	return dumps(value)
