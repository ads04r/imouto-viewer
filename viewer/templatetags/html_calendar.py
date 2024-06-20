from django import template
from django.utils.safestring import mark_safe
register = template.Library()
@register.filter(name='calendar')
def calendar(value, is_safe=True):
	i = value.days.first().date.weekday()
	ret = ""
	if i > 0:
		ret = ret + '<td colspan="' + str(i) + '"></td>'
	for d in range(0, value.days.count()):
		day_slug = (value.slug + "{:02}".format(d + 1)).replace('month', 'day')
		ret = ret + '<td><div class="text-center"><a href="#' + day_slug + '">' + str(d + 1) + '</a></div></td>'
		i = i + 1
		if i >= 7:
			ret = ret + '</tr><tr>'
			i = 0
	if i < 6:
		ret = ret + '<td colspan="' + str(7 - i) + '"></td>'
	return mark_safe('<table class="table table-condensed"><tr><th><small>Mon</small></th><th><small>Tue</small></th><th><small>Wed</small></th><th><small>Thu</small></th><th><small>Fri</small></th><th><small>Sat</small></th><th><small>Sun</small></th></tr><tr>' + ret + '</tr></table>'.replace('<tr></tr>', ''))
