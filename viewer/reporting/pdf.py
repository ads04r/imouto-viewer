from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, BalancedColumns, Frame
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from tempfile import NamedTemporaryFile
import random, json, markdown, os

class SectionTitle(Paragraph):

	def wrap(self, availWidth, availHeight):
		return Paragraph.wrap(self, availWidth, availHeight)
	def draw(self):
		Paragraph.draw(self)

def generate_year_story(year, styles):

	story = []
	if year.cached_wordcloud:
		story.append(Image(str(year.cached_wordcloud.file), width=18*cm, height=25*cm))
		story.append(PageBreakIfNotEmpty())
	for category in year.get_all_stat_categories():
		statboxes = []
		graphs = []
		stats = []
		row = []
		max_per_row = 3
		for stat in year.properties.filter(category=category):
			desc = ''
			if stat.description:
				desc = str(stat.description)
			row.append([Paragraph(str(stat.key), style=styles['Heading2']), Paragraph(str(stat.value), style=styles['Heading1']), Paragraph(desc, style=styles['Normal'])])
			if len(row) >= max_per_row:
				stats.append(row)
				row = []
		if len(row) > 0:
			stats.append(row)
		for chart in year.charts.filter(category=category):
			data = []
			for row in json.loads(chart.data):
				if not('text' in row):
					continue
				if not('value' in row):
					continue
				data.append([Paragraph(str(row['text']), style=styles['Normal']), Paragraph(str(row['value']), style=styles['Normal'])])
			if len(data) > 0:
				item = Table([[Paragraph(str(chart.text), style=styles['Heading2'])], [Table(data)]])
				statboxes.append(item)
		for graph in year.graphs.filter(category=category):
			if ((graph.type == 'donut') or (graph.type == 'pie')):
				piechart = Drawing(17*cm, 8*cm)
				pie = Pie()
				pie.x = 5.5*cm
				pie.y = 1*cm
				pie.width = 6*cm
				pie.height = 6*cm
				data = json.loads(graph.data)
				pie.data = data[1]
				pie.labels = data[0]
				pie.sideLabels = True
				piechart.add(pie)
				graphs.append(KeepTogether([Paragraph(graph.key, style=styles['Heading2']), piechart]))
		if (len(statboxes) + len(graphs) + len(stats)) > 0:
			story.append(Paragraph(str(year.year) + " in " + str(category), style=styles['Heading1']))
			if len(stats) > 0:
				story.append(Table(stats))
			if len(statboxes) > 0:
				if len(statboxes) == 1:
					story.append(statboxes[0]) # Take the whole page if there's only one item
				else:
					story.append(BalancedColumns(statboxes, nCols=2))
			if len(graphs) > 0:
				for graph in graphs:
					story.append(graph)
		story.append(PageBreakIfNotEmpty())
	for i in range(0, 12):
		month = Month.objects.get(year=year.year, month=(i + 1))
		for item in generate_month_story(month, styles):
			story.append(item)
	return story

def generate_life_event_story(event, styles):

	story = []
	items = []
	items.append(Paragraph(event.caption, style=styles['Heading1']))
	if event.description:
		md = markdown.Markdown()
		html = md.convert(event.description.replace('\n', '\n\n'))
		if event.cover_photo:
			file_path = str(event.cover_photo.file.path)
		items.append(Paragraph(html, style=styles['Normal']))
	item = KeepTogether(items)
	story.append(item)
	story.append(PageBreakIfNotEmpty())
	return story

def generate_month_story(month, styles):

	story = []
	table = []
	row = []
	max_people_per_row = 4
	photo_size = 2
	people = month.new_people()
	for person in people:
		tf = NamedTemporaryFile(delete=False)
		im = person.thumbnail(100)
		im.save(tf, format='JPEG')
		row.append([Image(tf.name, width=photo_size*cm, height=photo_size*cm), Paragraph(str(person.full_name()))])
		if len(row) >= max_people_per_row:
			table.append(row)
			row = []
	if len(row) > 0:
		table.append(row)
	story.append(SectionTitle(str(month), style=styles['Title']))
	story.append(PageBreakIfNotEmpty())
	if len(table) > 0:
		story.append(Paragraph("People", style=styles['Heading1']))
		story.append(Table(table))
		story.append(PageBreakIfNotEmpty())
	for event in month.life_events.order_by('start_time'):
		for item in generate_life_event_story(event, styles):
			story.append(item)
	for event in month.reportable_events().order_by('start_time'):
		if event.description:
			if event.cached_staticmap:
				story.append(Table(
					[
						[Paragraph(event.caption, style=styles['Heading2']), ''], 
						[Paragraph(event.description_html(), style=styles['Normal']), Image(str(event.cached_staticmap.file), width=6*cm, height=6*cm)]
					], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('SPAN', (0, 0), (1, 0))]))
			else:
				story.append(Table(
					[
						[Paragraph(event.caption, style=styles['Heading2'])],
						[Paragraph(event.description_html(), style=styles['Normal'])]
					], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (0, 1), 'TOP')]))
	story.append(PageBreakIfNotEmpty())
	for event in month.reportable_events().order_by('start_time'):
		if event.photo_collages.count() >= 1:
			story.append(Image(str(event.photo_collages.first().image.file), width=18*cm, height=25*cm))

	story.append(PageBreakIfNotEmpty())
	return story

#							Paragraph(event.start_time.strftime("%A %d %B, %I:%M"), style=styles['Italic']),

def generate_year_pdf(year, export_file, document_styles=None):

	doc = SimpleDocTemplate(export_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
	year = Year.objects.get(year=year)
	if document_styles is None:
		styles = getSampleStyleSheet()
	else:
		styles = document_styles
	doc.build(generate_year_story(year, styles))


