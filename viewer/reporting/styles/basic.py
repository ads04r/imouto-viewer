from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, BaseDocTemplate, PageTemplate, Spacer
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet as get_stylesheet_template
from reportlab.lib.units import inch, cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from django.conf import settings
from tempfile import NamedTemporaryFile

from viewer.functions.locations import home_location

import random, json, markdown, os

import logging
logger = logging.getLogger(__name__)

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

class ImoutoDocTemplate(BaseDocTemplate):

	def __init__(self, filename, layout, **kw):
		BaseDocTemplate.__init__(self, filename, **dict(kw))
		self.addPageTemplates(layout)
		self.indexobject = SimpleIndex(dot=' . ', headers=True)

	def afterFlowable(self, flowable):
		if flowable.__class__.__name__ == 'Paragraph':
			text = flowable.getPlainText()
			style = flowable.style.name
			level = -1
			if style == 'SectionTitle':
				level = 0
			if style == 'CentredHeading':
				level = 0
			if style == 'StatsPageTitle':
				level = 1
			if style == 'LifeEventTitle':
				level = 1
			if level > -1:
				item = [level, text, self.page]
				link = getattr(flowable, '_bookmarkName', None)
				if link is not None:
					item.append(link)
				self.notify('TOCEntry', tuple(item))

	def multiBuild(self, story, **kw):
		story.append(NextPageTemplate('IndexPage'))
		story.append(PageBreak())
		story.append(self.indexobject)
		BaseDocTemplate.multiBuild(self, story, **dict(kw, canvasmaker=self.indexobject.getCanvasMaker()))

class ImoutoBasicReportStyle():

	def __init__(self, year):
		self.year = year
		self.page_size = A4
		self.top_margin = 2*cm
		self.bottom_margin = 2*cm
		self.left_margin = 2*cm
		self.right_margin = 2*cm
		self.primary_colour = [0.5, 0, 0]
		self.secondary_colour = [0, 0, 0.5]
		self.tertiary_colour = [0, 0.5, 0]
		self.title_font = 'Helvetica-Bold'
		self.main_font = 'Times-Roman'

	@property
	def page_width(self):
		return self.page_size[0]

	@property
	def page_height(self):
		return self.page_size[1]

	@property
	def content_width(self):
		return self.page_size[0] - (self.left_margin + self.right_margin)

	@property
	def content_height(self):
		return self.page_size[1] - (self.top_margin + self.bottom_margin)

	def generate(self, export_file):
		logger.info("Generating BASIC report for " + str(self.year))
		logger.debug("Saving as " + export_file)
		doc = ImoutoDocTemplate(export_file, self.getLayout(), pagesize=self.page_size, rightMargin=self.right_margin, leftMargin=self.left_margin, topMargin=self.top_margin, bottomMargin=self.bottom_margin)
		report = Year.objects.get(year=self.year)
		doc.multiBuild(self.generate_year_story())

	def getLayout(self):

		def __header(canvas, doc):
			canvas.saveState()
			canvas.restoreState()

		def __footer(canvas, doc):
			canvas.saveState()
			canvas.setFont(self.main_font, 12)
			text = 'Page ' + str(doc.page)
			canvas.setLineWidth(2)
			canvas.line(doc.leftMargin, doc.bottomMargin, doc.width + doc.leftMargin, doc.bottomMargin)
			canvas.line(doc.leftMargin, doc.bottomMargin + doc.height, doc.width + doc.leftMargin, doc.bottomMargin + doc.height)
			if doc.page % 2 == 0:
				canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			else:
				canvas.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			canvas.restoreState()

		column_width = (self.content_width / 2) - 6
		return [PageTemplate(id='TitlePage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='titlepage')),
			PageTemplate(id='FullPage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='fullpage')),
			PageTemplate(id='FullPageBlock', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='fullpageblock')),
			PageTemplate(id='LifeEventPage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='lifeeventpage'), onPage=__header, onPageEnd=__footer),
			PageTemplate(id='PeoplePage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='peoplepage'), onPage=__header, onPageEnd=__footer),
			PageTemplate(id='EventsPage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='eventspage'), onPage=__header, onPageEnd=__footer),
			PageTemplate(id='Normal', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='normal'), onPage=__header, onPageEnd=__footer),
			PageTemplate(id='StatsPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPage=__header, onPageEnd=__footer),
			PageTemplate(id='ContentsPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPage=__header, onPageEnd=__footer),
			PageTemplate(id='IndexPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPage=__header, onPageEnd=__footer)]

	def getStyles(self):

		sss = get_stylesheet_template()
		ret = {}

		ret['Title'] = sss['Title']
		ret['Normal'] = sss['Normal']
		ret['Heading1'] = sss['Heading1']
		ret['Heading2'] = sss['Heading2']
		ret['Heading3'] = sss['Heading3']
		ret['Heading4'] = sss['Heading4']

		ret['YearTitle'] = ParagraphStyle('YearTitle', parent=sss['Title'], fontName=self.title_font, alignment=1, textTransform='uppercase', fontSize=100, leading=120)
		ret['SectionTitle'] = ParagraphStyle('SectionTitle', parent=sss['Title'], fontName=self.title_font, alignment=1, textTransform='uppercase', fontSize=36, leading=40)
		ret['SectionSubTitle'] = ParagraphStyle('SectionTitle', parent=sss['Title'], fontName=self.title_font, alignment=1, textTransform='uppercase')
		ret['ChartTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
		ret['GraphTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
		ret['StatsPageTitle'] = ParagraphStyle('StatsPageTitle', parent=sss['Heading1'], fontName=self.title_font, alignment=1)
		ret['LifeEventTitle'] = ParagraphStyle('LifeEventTitle', parent=sss['Heading1'], fontName=self.title_font, alignment=1)
		ret['EventTitle'] = ParagraphStyle('EventTitle', parent=sss['Heading2'], fontName=self.title_font, backColor='#CFCFCF')
		ret['EventDate'] = ParagraphStyle('EventDate', parent=sss['Normal'], fontName=self.main_font)
		ret['EventText'] = ParagraphStyle('EventText', parent=sss['Normal'], fontName=self.main_font)
		ret['StatisticTitle'] = ParagraphStyle('StatisticTitle', parent=sss['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
		ret['StatisticValue'] = ParagraphStyle('StatisticValue', parent=sss['Heading1'], fontName=self.title_font, alignment=1, spaceBefore=0, spaceAfter=0)
		ret['StatisticDescription'] = ParagraphStyle('StatisticDescription', parent=sss['Normal'], fontName=self.main_font, alignment=1, spaceBefore=0, spaceAfter=1.5*cm)

		return ret

	def generate_year_story(self):

		year = Year.objects.get(year=self.year)
		styles = self.getStyles()

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
					graphs.append(self.graph_to_flowable(str(graph.key), json.loads(graph.data), styles))
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
			logger.debug("Generating " + str(month))
			month_story = self.generate_month_story(month)
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

	def generate_life_event_story(self, event):

		story = []
		photo_collages = []
		events = []
		styles = self.getStyles()
		for e in event.subevents().order_by('start_time'):
			for c in e.photo_collages.all():
				photo_collages.append(Image(str(c.image.file), width=18*cm, height=25*cm))
			if ((e.description) or (e.cached_staticmap)):
				events.append(self.event_to_flowable(e))

		story.append(Paragraph(event.caption, style=styles['LifeEventTitle']))
		if event.cover_photo:
			tf = NamedTemporaryFile(delete=False)
			im = event.cover_photo.thumbnail(200)
			im.save(tf, format='JPEG')
			story.append(Table(
				[
					[Paragraph(self.event_to_indices(event) + event.description_html(), style=styles['Normal']), Image(str(tf.name), width=6*cm, height=6*cm)]
				], colWidths=[None, 7*cm], style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1))]))
		else:
			story.append(Paragraph(self.event_to_indices(event) + event.description_html(), style=styles['Normal']))
		if len(events) > 0:
			story.append(NextPageTemplate('EventsPage'))
			story.append(PageBreakIfNotEmpty())
			for e in events:
				story.append(e)
		if len(photo_collages) > 0:
			story.append(NextPageTemplate('FullPageBlock'))
			story.append(PageBreakIfNotEmpty())
			for c in photo_collages:
				story.append(c)
		return remove_multiple_page_breaks(story)

	def graph_to_flowable(self, title, data, styles):
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

	def event_to_flowable(self, event):
		ret = None
		html = self.event_to_indices(event) + event.description_html()
		styles = self.getStyles()
		if event.cached_staticmap:
			ret = Table(
				[
					[Paragraph(event.caption, style=styles['EventTitle']), ''],
					[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])], Image(str(event.cached_staticmap.file), width=6*cm, height=6*cm)]
				], colWidths=[None, 7*cm], splitInRow=2, style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
		elif event.cover_photo:
			tf = NamedTemporaryFile(delete=False)
			im = event.cover_photo.thumbnail(200)
			im.save(tf, format='JPEG')
			ret = Table(
				[
					[Paragraph(event.caption, style=styles['EventTitle']), ''],
					[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])], Image(str(tf.name), width=6*cm, height=6*cm)]
				], colWidths=[None, 7*cm], splitInRow=2, style=[('VALIGN', (0, 0), (1, 2), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1)), ('SPAN', (0, 0), (1, 0))])
		else:
			ret = Table(
				[
					[Paragraph(event.caption, style=styles['EventTitle'])],
					[[Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])]]
				], colWidths=[None, 7*cm], splitInRow=2, style=[('VALIGN', (0, 0), (0, 1), 'TOP'), ('NOSPLIT', (0, 0), (-1, -1))])
		return ret

	def event_to_indices(self, event):
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
			person_name = str(person.sort_name).strip()
			if person_name == '':
				continue
			ret = ret + '<index item="' + person_name.replace(', ', ',, ') + '" />'
		if event.location:
			ret = ret + '<index item="' + str(event.location.sort_name()).replace(', ', ',, ') + '" />'
			if event.location.city:
				if event.location.city != home_city:
					city_name = str(event.location.city).strip()
					if city_name != '':
						ret = ret + '<index item="' + city_name.replace(', ', ',, ') + '" />'
			if event.location.country:
				if event.location.country != home_country:
					country_name = str(event.location.country).strip()
					if country_name != '':
						ret = ret + '<index item="' + country_name.replace(', ', ',, ') + '" />'

		logger.debug("INDEX: " + ret)
		return ret

	def generate_month_title(self, month):

		story = []
		styles = self.getStyles()
		story.append(Spacer(10*cm, 10*cm))
		story.append(Paragraph(str(month), style=styles['SectionTitle']))
		return story

	def generate_month_story(self, month):

		story = []
		table = []
		row = []
		max_people_per_row = 4
		photo_size = 2
		people = month.new_people
		styles = self.getStyles()
		for person in people:
			if not(person.image or person.significant):
				continue
			tf = NamedTemporaryFile(delete=False)
			im = person.thumbnail(100)
			im.save(tf, format='JPEG')
			row.append([Image(tf.name, width=photo_size*cm, height=photo_size*cm), Paragraph(str(person.full_name), style=ParagraphStyle('Centred', parent=styles['Normal'], alignment=1))])
			if len(row) >= max_people_per_row:
				table.append(row)
				row = []
		life_events = month.life_events.order_by('start_time')
		if len(row) > 0:
			table.append(row)
		for item in self.generate_month_title(month):
			story.append(item)
		story.append(NextPageTemplate('StatsPage'))
		story.append(PageBreakIfNotEmpty())
		story.append(Spacer(cm, cm))
		for workout in month.workouts:
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
		lc = month.location_categories
		for item in lc:
			lc_data[0].append(str(item[0]))
			lc_data[1].append(item[1])
		if len(lc) > 0:
			story.append(self.graph_to_flowable("Most visited places", lc_data, styles))
		longest_journey = month.longest_journey
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
			story.append(PageBreakIfNotEmpty())
			story.append(Paragraph("People", style=styles['Heading1']))
			story.append(Table(table, style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]))

		collages = 0
		descriptions = 0
		for event in month.reportable_events:
			if event.description:
				descriptions = descriptions + 1
			if event.photo_collages.count() >= 1:
				collages = collages + 1

		logger.debug(str(month) + " has " + str(life_events.count()) + " life event(s)")
		if life_events.count() > 0:
			story.append(NextPageTemplate('LifeEventPage'))
			story.append(PageBreakIfNotEmpty())

		i = 0
		for event in life_events:
			for item in self.generate_life_event_story(event):
				story.append(item)
			i = i + 1
			if i < life_events.count():
				story.append(NextPageTemplate('LifeEventPage'))
				story.append(PageBreakIfNotEmpty())
		if descriptions > 0:
			story.append(NextPageTemplate('EventsPage'))
			story.append(PageBreakIfNotEmpty())
			for event in month.reportable_events.order_by('start_time'):
				if event.description:
					story.append(self.event_to_flowable(event))
		if collages > 0:
			story.append(NextPageTemplate('FullPageBlock'))
			story.append(PageBreakIfNotEmpty())
			for event in month.reportable_events.order_by('start_time'):
				if event.photo_collages.count() >= 1:
					story.append(Image(str(event.photo_collages.first().image.file), width=18*cm, height=25*cm))

		return remove_multiple_page_breaks(story)



