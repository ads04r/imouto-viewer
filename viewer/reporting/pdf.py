from reportlab.platypus import PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, Frame, Spacer
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from django.conf import settings
from tempfile import NamedTemporaryFile
import random, json, markdown, os
from viewer.reporting.styles.basic import ImoutoSampleYearTemplate, ImoutoSampleMonthTemplate, getSampleStyleSheet
from viewer.functions.locations import home_location

def remove_multiple_page_breaks(story):

	ret = []
	for item in story:
		if len(ret) == 0:
			ret.append(item)
			continue
		if isinstance(ret[-1], PageBreakIfNotEmpty):
			if isinstance(item, PageBreakIfNotEmpty):
				continue
		ret.append(item)
	return ret

def generate_year_story(year, styles):

	story = []
	story.append(Spacer(10*cm, 8*cm))
	story.append(Paragraph(str(year.year), style=styles['YearTitle']))
	story.append(Paragraph(str(year.caption), style=styles['SectionSubTitle']))
	if year.cached_wordcloud:
		story.append(NextPageTemplate('FullPage'))
		story.append(PageBreakIfNotEmpty())
		story.append(Image(str(year.cached_wordcloud.file), width=18*cm, height=25*cm))
	story.append(NextPageTemplate('ContentsPage'))
	story.append(PageBreakIfNotEmpty())
	story.append(Paragraph("Contents", style=styles['Heading1']))
	story.append(TableOfContents())
	for category in year.get_all_stat_categories() + ['']:
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
			data = [[Paragraph(str(chart.text), style=styles['ChartTitle']), '']]
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
			if len(category) == 0:
				story.append(Paragraph(str(year.year) + " Miscellaneous", style=styles['StatsPageTitle']))
			else:
				story.append(Paragraph(str(year.year) + " in " + str(category).capitalize(), style=styles['StatsPageTitle']))
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
		month = Month.objects.get(year=year.year, month=(i + 1))
		month_story = generate_month_story(month, styles)
		if len(month_story) < 10:
			continue
		month_flowables = []
		paragraphs = []
		for item in month_story:
			item_type = str(item.__class__.__name__)
			if item_type == 'Paragraph':
				paragraphs.append(item.getPlainText())
			if item_type in month_flowables:
				continue
			month_flowables.append(item_type)
		story.append(NextPageTemplate('TitlePage'))
		story.append(PageBreakIfNotEmpty())
		for item in month_story:
			story.append(item)
	return remove_multiple_page_breaks(story)

def generate_life_event_story(event, styles):

	story = []
	photo_collages = []
	events = []
	for e in event.subevents().order_by('start_time'):
		for c in e.photo_collages.all():
			photo_collages.append(Image(str(c.image.file), width=18*cm, height=25*cm))
		if ((e.description) or (e.cached_staticmap)):
			events.append(event_to_flowable(e, styles))

	story.append(Paragraph(event.caption, style=styles['LifeEventTitle']))
	if event.cover_photo:
		tf = NamedTemporaryFile(delete=False)
		im = event.cover_photo.thumbnail(200)
		im.save(tf, format='JPEG')
		story.append(Table(
			[
				[Paragraph(event_to_indices(event) + event.description_html(), style=styles['Normal']), Image(str(tf.name), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1))]))
	else:
		story.append(Paragraph(event_to_indices(event) + event.description_html(), style=styles['Normal']))
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
	return remove_multiple_page_breaks(story)

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
	html = event_to_indices(event) + event.description_html()
	if event.cached_staticmap:
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle']), ''],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])], Image(str(event.cached_staticmap.file), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
	elif event.cover_photo:
		tf = NamedTemporaryFile(delete=False)
		im = event.cover_photo.thumbnail(200)
		im.save(tf, format='JPEG')
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle']), ''],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])], Image(str(tf.name), width=6*cm, height=6*cm)]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
	else:
		ret = Table(
			[
				[Paragraph(event.caption, style=styles['EventTitle'])],
				[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])]]
			], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (0, 1), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1))])
	return ret

def event_to_indices(event):
	ret = ''
	home = home_location()
	if home is None:
		home_city = None
		home_country = None
	else:
		home_city = home.city
		home_country = home.country
		if home_country is None:
			home_country = home.city.country
	for tag in event.tags.all():
		tag_name = str(tag).capitalize()
		if tag_name == '':
			continue
		ret = ret + '<index item="' + tag_name.replace(', ', ',, ') + '" />'
	for person in event.people.all():
		ret = ret + '<index item="' + str(person.sort_name()).replace(', ', ',, ') + '" />'
	if event.location:
		ret = ret + '<index item="' + str(event.location.sort_name()).replace(', ', ',, ') + '" />'
		if event.location.city:
			if event.location.city != home_city:
				ret = ret + '<index item="' + str(event.location.city).replace(', ', ',, ') + '" />'
		if event.location.country:
			if event.location.country != home_country:
				ret = ret + '<index item="' + str(event.location.country).replace(', ', ',, ') + '" />'
	return ret

def generate_month_story(month, styles):

	story = []
	table = []
	row = []
	max_people_per_row = 4
	photo_size = 2
	people = month.new_people()
	for person in people:
		if not(person.image or person.significant):
			continue
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
		if not(im is None):
			im.save(tf, format='PNG')
			lj_table = []
			lj_table.append([Spacer(cm, cm)])
			lj_table.append([Paragraph("Longest Journey", style=styles['StatisticTitle'])])
			lj_table.append([Image(str(tf.name), width=6*cm, height=6*cm)])
			lj_table.append([Paragraph(str(int(longest_journey.distance() + 0.5)) + " miles", style=styles['StatisticValue'])])
			lj_table.append([Paragraph(longest_journey.start_time.strftime("%A %-d %B"), style=styles['StatisticDescription'])])
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

	return remove_multiple_page_breaks(story)

def generate_year_pdf(year, export_file, stylesheet=None):

	styles = stylesheet
	if styles is None:
		styles = getSampleStyleSheet()
	doc = ImoutoSampleYearTemplate(export_file)
	report = Year.objects.get(year=year)
	doc.multiBuild(generate_year_story(report, styles))

def generate_month_pdf(year, month, stylesheet=None):

	styles = stylesheet
	if styles is None:
		styles = getSampleStyleSheet()
	doc = ImoutoSampleMonthTemplate(export_file)
	report = Month.objects.get(year=year, month=month)
	doc.multiBuild(generate_month_story(report, styles))
