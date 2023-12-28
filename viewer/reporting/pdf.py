from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from viewer.models.core import Year, Month, Day, Event
import random

def generate_month_story(month, styles):

	story = []
	for event in month.life_events.order_by('start_time'):
		items = []
		items.append(Paragraph(event.caption, style=styles['Heading1']))
		if event.description:
			for p in event.description.split('\n'):
				items.append(Paragraph(p.strip(), style=styles['Normal']))
		item = KeepTogether(items)
		story.append(item)
	return story

def generate_test_document(export_file):

	doc = SimpleDocTemplate(export_file, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
	month = Month.objects.get(year=2023, month=5)
	doc.build(generate_month_story(month, getSampleStyleSheet()))


