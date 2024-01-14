from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, Frame, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from tempfile import NamedTemporaryFile
import random, json, markdown, os

def imouto_sample_layout(doc):

	return [PageTemplate(id='TitlePage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='titlepage')),
		PageTemplate(id='FullPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='fullpage')),
		PageTemplate(id='LifeEventPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='lifeeventpage'), onPageEnd=imouto_sample_footer),
		PageTemplate(id='PeoplePage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='peoplepage'), onPageEnd=imouto_sample_footer),
		PageTemplate(id='EventsPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='eventspage'), onPageEnd=imouto_sample_footer),
		PageTemplate(id='Normal', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal'), onPageEnd=imouto_sample_footer),
		PageTemplate(id='StatsPage', frames=[
			Frame(doc.leftMargin, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col1'),
			Frame(doc.leftMargin + (doc.width / 2) + 6, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col2')
		], onPageEnd=imouto_sample_footer)]

def imouto_sample_stylesheet():

	sss = getSampleStyleSheet()
	ret = {}

	ret['Title'] = sss['Title']
	ret['Normal'] = sss['Normal']
	ret['Heading1'] = sss['Heading1']
	ret['Heading2'] = sss['Heading2']
	ret['Heading3'] = sss['Heading3']
	ret['Heading4'] = sss['Heading4']

	ret['YearTitle'] = ParagraphStyle('YearTitle', parent=sss['Title'], alignment=1, textTransform='uppercase', fontSize=100, leading=120)
	ret['SectionTitle'] = ParagraphStyle('SectionTitle', parent=sss['Title'], alignment=1, textTransform='uppercase', fontSize=36, leading=40)
	ret['SectionSubTitle'] = ParagraphStyle('SectionTitle', parent=sss['Title'], alignment=1, textTransform='uppercase')
	ret['GraphTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', spaceBefore=cm, spaceAfter=0)
	ret['EventTitle'] = ParagraphStyle('EventTitle', parent=sss['Heading2'])
	ret['EventDate'] = ParagraphStyle('EventDate', parent=sss['Normal'])
	ret['EventText'] = ParagraphStyle('EventText', parent=sss['Normal'])
	ret['StatisticTitle'] = ParagraphStyle('StatisticTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', spaceBefore=cm, spaceAfter=0)
	ret['StatisticValue'] = ParagraphStyle('StatisticValue', parent=sss['Heading1'], alignment=1, spaceBefore=0, spaceAfter=0)
	ret['StatisticDescription'] = ParagraphStyle('StatisticDescription', parent=sss['Normal'], alignment=1, spaceBefore=0, spaceAfter=1.5*cm)

	return ret

def imouto_sample_footer(canvas, doc):
	canvas.saveState()
	canvas.setFont('Times-Roman', 12)
	text = 'Page ' + str(doc.page)
	canvas.setLineWidth(2)
	canvas.line(doc.leftMargin, doc.bottomMargin, doc.width + doc.leftMargin, doc.bottomMargin)
	canvas.line(doc.leftMargin, doc.bottomMargin + doc.height, doc.width + doc.leftMargin, doc.bottomMargin + doc.height)
	if doc.page % 2 == 0:
		canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
	else:
		canvas.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
	canvas.restoreState()

def generate_year_story(year, styles):

	story = []
	story.append(Spacer(10*cm, 8*cm))
	story.append(Paragraph(str(year.year), style=styles['YearTitle']))
	story.append(Paragraph(str(year.caption), style=styles['SectionSubTitle']))
	if year.cached_wordcloud:
		story.append(NextPageTemplate('FullPage'))
		story.append(PageBreakIfNotEmpty())
		story.append(Image(str(year.cached_wordcloud.file), width=18*cm, height=25*cm))
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
				graphs.append(graph_to_flowable(str(graph.key), json.loads(graph.data), styles))
		if (len(stats) + len(graphs)) > 0:
			story.append(NextPageTemplate('StatsPage'))
			story.append(PageBreakIfNotEmpty())
			story.append(Paragraph(str(year.year) + " in " + str(category), style=styles['Heading1']))
			story.append(Spacer(cm, cm))
			for s in stats:
				story.append(s)
				story.append(Spacer(cm, cm))
			for g in graphs:
				story.append(g)
				story.append(Spacer(cm, cm))
			for c in charts:
				story.append(c)
				story.append(Spacer(cm, cm))
	for i in range(0, 12):
		story.append(NextPageTemplate('TitlePage'))
		story.append(PageBreakIfNotEmpty())
		month = Month.objects.get(year=year.year, month=(i + 1))
		for item in generate_month_story(month, styles):
			story.append(item)
	return story

def generate_life_event_story(event, styles):

	story = []
	photo_collages = []
	events = []
	for e in event.subevents().order_by('start_time'):
		for c in e.photo_collages.all():
			photo_collages.append(Image(str(c.image.file), width=18*cm, height=25*cm))
		if ((e.description) or (e.cached_staticmap)):
			events.append(event_to_flowable(e, styles))

	if event.cover_photo:
		tf = NamedTemporaryFile(delete=False)
		im = event.cover_photo.thumbnail(200)
		im.save(tf, format='JPEG')
		story.append(Table(
			[
				[Paragraph(event.caption, style=ParagraphStyle('CentredHeading', parent=styles['Heading1'], alignment=1)), ''],
				[Paragraph(event.description_html(), style=styles['Normal']), Image(str(tf.name), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))]))
	else:
		story.append(KeepTogether(Paragraph(event.caption, style=styles['Heading1']), Paragraph(event.description_html(), style=styles['Normal'])))
	if len(events) > 0:
		story.append(NextPageTemplate('EventsPage'))
		story.append(PageBreakIfNotEmpty())
		for e in events:
			story.append(e)
	if len(photo_collages) > 0:
		story.append(NextPageTemplate('FullPage'))
		story.append(PageBreakIfNotEmpty())
		for c in photo_collages:
			story.append(c)
	return story

def graph_to_flowable(title, data, styles):
	piechart = Drawing(8*cm, 8*cm)
	pie = Pie()
	pie.x = 2*cm
	pie.y = 2.5*cm
	pie.width = 4*cm
	pie.height = 4*cm
	pie.data = data[1]
	pie.labels = data[0]
	pie.sideLabels = True
	piechart.add(pie)
	return Table([[Paragraph(title, style=styles['GraphTitle'])], [piechart]], style=[('NOSPLIT', (0, 0), (-1, -1))])

def event_to_flowable(event, styles):
	ret = None
	if event.cached_staticmap:
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle']), ''],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(event.description_html(), style=styles['EventText'])], Image(str(event.cached_staticmap.file), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
	elif event.cover_photo:
		tf = NamedTemporaryFile(delete=False)
		im = event.cover_photo.thumbnail(200)
		im.save(tf, format='JPEG')
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle']), ''],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(event.description_html(), style=styles['EventText'])], Image(str(tf.name), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
	else:
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle'])],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(event.description_html(), style=styles['EventText'])]]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (0, 1), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1))])
	return ret

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
		row.append([Image(tf.name, width=photo_size*cm, height=photo_size*cm), Paragraph(str(person.full_name()), style=ParagraphStyle('Centred', parent=styles['Normal'], alignment=1))])
		if len(row) >= max_people_per_row:
			table.append(row)
			row = []
	life_events = month.life_events.order_by('start_time')
	if len(row) > 0:
		table.append(row)
	story.append(Spacer(10*cm, 10*cm))
	story.append(Paragraph(str(month), style=styles['SectionTitle']))
	story.append(NextPageTemplate('StatsPage'))
	story.append(PageBreakIfNotEmpty())

	story.append(Spacer(cm, cm))
	for workout in month.workouts():
		story.append(Table([
			[Paragraph(workout[0] + " distance", style=styles['StatisticTitle'])], 
			[Paragraph(str(workout[1]) + " miles", style=styles['StatisticValue'])], 
			[Paragraph('', style=styles['StatisticDescription'])]
			], style=[('ALIGN', (0, 0), (0, 3), 'CENTER'), ('VALIGN', (0, 0), (0, 3), 'TOP')]))
		story.append(Spacer(cm, cm))
	cities = []
	for city in month.cities:
		if len(cities) == 0:
			cities.append([Paragraph("Cities Visited", style=styles['StatisticTitle'])])
		cities.append([str(city)])
	if len(cities) > 0:
		item = Table(cities, style=[
				('VALIGN', (0, 0), (-1, -1), 'TOP'),
				('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
				('NOSPLIT', (0, 0), (-1, -1))
			])
		story.append(item)
		story.append(Spacer(cm, cm))
	lc_data = [[], []]
	lc = month.location_categories()
	for item in lc:
		lc_data[0].append(str(item[0]))
		lc_data[1].append(item[1])
	if len(lc) > 0:
		story.append(graph_to_flowable("Most visited places", lc_data, styles))
	longest_journey = month.longest_journey()
	if longest_journey:
		tf = NamedTemporaryFile(delete=False)
		im = longest_journey.staticmap()
		im.save(tf, format='PNG')
		lj_table = []
		lj_table.append([Spacer(cm, cm)])
		lj_table.append([Paragraph("Longest Journey", style=styles['StatisticTitle'])])
		lj_table.append([Image(str(tf.name), width=6*cm, height=6*cm)])
		story.append(Table(lj_table, style=[
			('VALIGN', (0, 0), (-1, -1), 'TOP'),
			('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
			('NOSPLIT', (0, 0), (-1, -1))
		]))

	if len(table) > 0:
		story.append(NextPageTemplate('PeoplePage'))
	else:
		if life_events.count == 0:
			story.append(NextPageTemplate('EventsPage'))
		else:
			story.append(NextPageTemplate('LifeEventPage'))
	story.append(PageBreakIfNotEmpty())
	if len(table) > 0:
		story.append(Paragraph("People", style=styles['Heading1']))
		story.append(Table(table, style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
		story.append(NextPageTemplate('EventsPage'))
		story.append(PageBreakIfNotEmpty())

	for event in life_events:
		for item in generate_life_event_story(event, styles):
			story.append(item)
	if life_events.count() > 0:
		story.append(NextPageTemplate('EventsPage'))
		story.append(PageBreakIfNotEmpty())
	for event in month.reportable_events().order_by('start_time'):
		if event.description:
			story.append(event_to_flowable(event, styles))
	story.append(NextPageTemplate('FullPage'))
	story.append(PageBreakIfNotEmpty())
	for event in month.reportable_events().order_by('start_time'):
		if event.photo_collages.count() >= 1:
			story.append(Image(str(event.photo_collages.first().image.file), width=18*cm, height=25*cm))

	return story

def generate_year_pdf(year, export_file, stylesheet=None, layout=None):

	doc = BaseDocTemplate(export_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
	if layout is None:
		doc.addPageTemplates(imouto_sample_layout(doc))
	else:
		doc.addPageTemplates(layout)
	report = Year.objects.get(year=year)
	if stylesheet is None:
		styles = imouto_sample_stylesheet()
	else:
		styles = stylesheet
	doc.build(generate_year_story(report, styles))

def generate_month_pdf(year, month, export_file, stylesheet=None, layout=None):

	doc = BaseDocTemplate(export_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
	if layout is None:
		doc.addPageTemplates(imouto_sample_layout(doc))
	else:
		doc.addPageTemplates(layout)
	report = Month.objects.get(year=year, month=month)
	if stylesheet is None:
		styles = imouto_sample_stylesheet()
	else:
		styles = stylesheet
	doc.build(generate_month_story(report, styles))
