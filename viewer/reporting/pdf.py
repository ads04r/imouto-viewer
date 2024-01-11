from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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

def imouto_sample_layout(doc):

	return [PageTemplate(id='FullPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')),
		PageTemplate(id='TwoColumns', frames=[
			Frame(doc.leftMargin, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col1'),
			Frame(doc.leftMargin + (doc.width / 2) + 6, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col2')
		], onPage=render_footer)]

def imouto_sample_stylesheet():

	sss = getSampleStyleSheet()
	ret = {}

	ret['Title'] = sss['Title']
	ret['Normal'] = sss['Normal']
	ret['Heading1'] = sss['Heading1']
	ret['Heading2'] = sss['Heading2']
	ret['Heading3'] = sss['Heading3']
	ret['Heading4'] = sss['Heading4']

	ret['GraphTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', spaceBefore=cm, spaceAfter=0)
	ret['StatisticTitle'] = ParagraphStyle('StatisticTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', spaceBefore=cm, spaceAfter=0)
	ret['StatisticValue'] = ParagraphStyle('StatisticValue', parent=sss['Heading1'], alignment=1, spaceBefore=0, spaceAfter=0)
	ret['StatisticDescription'] = ParagraphStyle('StatisticDescription', parent=sss['Normal'], alignment=1, spaceBefore=0, spaceAfter=1.5*cm)

	return ret

def generate_year_story(year, styles):

	story = []
	if year.cached_wordcloud:
		story.append(Image(str(year.cached_wordcloud.file), width=18*cm, height=25*cm))
		story.append(NextPageTemplate('TwoColumns'))
		story.append(PageBreakIfNotEmpty())
	for category in year.get_all_stat_categories():
		stats = []
		graphs = []
		charts = []
		for stat in year.properties.filter(category=category):
			desc = ''
			if stat.description:
				desc = str(stat.description)
			stats.append(Table([
				[Paragraph(str(stat.key), style=styles['StatisticTitle'])], 
				[Paragraph(str(stat.value), style=styles['StatisticValue'])], 
				[Paragraph(desc, style=styles['StatisticDescription'])]
				], style=[('ALIGN', (0, 0), (0, 3), 'CENTER'), ('VALIGN', (0, 0), (0, 3), 'TOP')]))
		for chart in year.charts.filter(category=category):
			data = [[Paragraph(str(chart.text), style=styles['Heading2']), '']]
			for row in json.loads(chart.data):
				if not('text' in row):
					continue
				if not('value' in row):
					continue
				data.append([str(row['text']), str(row['value'])])
			if len(data) > 0:
				item = Table(data, style=[
						('VALIGN', (0, 0), (-1, -1), 'TOP'),
						('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
						('NOSPLIT', (0, 0), (-1, -1)),
						('SPAN', (0, 0), (1, 0))
					])
				charts.append(item)
		for graph in year.graphs.filter(category=category):
			if ((graph.type == 'donut') or (graph.type == 'pie')):
				piechart = Drawing(8*cm, 8*cm)
				pie = Pie()
				pie.x = 2*cm
				pie.y = 2.5*cm
				pie.width = 4*cm
				pie.height = 4*cm
				data = json.loads(graph.data)
				pie.data = data[1]
				pie.labels = data[0]
				pie.sideLabels = True
				piechart.add(pie)
				graphs.append(Table([[Paragraph(graph.key, style=styles['GraphTitle'])], [piechart]], style=[('NOSPLIT', (0, 0), (-1, -1))]))
		if (len(stats) + len(graphs)) > 0:
			story.append(NextPageTemplate('TwoColumns'))
			story.append(PageBreakIfNotEmpty())
			story.append(Paragraph(str(year.year) + " in " + str(category), style=styles['Heading1']))
			for s in stats:
				story.append(s)
			for g in graphs:
				story.append(g)
			for c in charts:
				story.append(c)
	story.append(NextPageTemplate('FullPage'))
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

def render_footer(canvas, doc):
	canvas.saveState()
	canvas.setFont('Times-Roman', 9)
	canvas.drawString(cm, cm, "Page %d" % doc.page)
	canvas.restoreState()

def generate_year_pdf(year, export_file, stylesheet=None, layout=None):

	doc = SimpleDocTemplate(export_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
	if layout is None:
		doc.addPageTemplates(imouto_sample_layout(doc))
	else:
		doc.addPageTemplates(layout)
	year = Year.objects.get(year=year)
	if stylesheet is None:
		styles = imouto_sample_stylesheet()
	else:
		styles = stylesheet
	doc.build(generate_year_story(year, styles))

