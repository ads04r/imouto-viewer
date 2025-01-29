from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, FrameBreak, PageBreakIfNotEmpty, BaseDocTemplate, PageTemplate, Spacer
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import Color
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from django.conf import settings
from tempfile import NamedTemporaryFile

from viewer.reporting.styles.basic import ImoutoBasicReportStyle, ImoutoDocTemplate, remove_multiple_page_breaks

import random, json, markdown, os

import logging
logger = logging.getLogger(__name__)
page_count = 0

class EventTable(Table):

	def draw(self):
		global page_count
		if page_count % 2 == 1:
			logger.debug("Generating RH page ... " + str(repr(self._colWidths)) + " " + str(repr(self._colpositions)))
			super().draw()
		else:
			self._curweight = self._curcolor = self._curcellstyle = None
			self._drawBkgrnd()
			colpos = [0]
			colwidth = list(reversed(self._colWidths))
			colwidth[0] = colwidth[0] + int(cm / 2)
			for w in colwidth:
				cum = colpos[-1] + w
				colpos.append(cum)
			logger.debug("Generating LH page ... " + str(repr(colwidth)) + " " + str(repr(colpos)))
			for row, rowstyle, rowpos, rowheight in zip(self._cellvalues, self._cellStyles, self._rowpositions[1:], self._rowHeights):
				for cellval, cellstyle, colpos, colwidth in zip(list(reversed(row)), list(rowstyle), colpos, colwidth):
					self._drawCell(cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight))

class EventImage(Image):

	def __init__(self, filename, width=None, height=None, kind='direct', mask='auto', lazy=1, hAlign='CENTER', useDPI=False):
		self.height = height
		super().__init__(filename=filename, width=width, height=height, kind=kind, mask=mask, lazy=lazy, hAlign=hAlign, useDPI=useDPI)

class ImoutoMinimalistTemplate(ImoutoDocTemplate):

	def afterFlowable(self, flowable):
		if flowable.__class__.__name__ == 'Paragraph':
			text = flowable.getPlainText()
			style = flowable.style.name
			level = -1
			if style == 'SectionSubTitle':
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

class ImoutoMinimalistReportStyle(ImoutoBasicReportStyle):

	def __init__(self, *args, **kwargs):
		super(ImoutoMinimalistReportStyle, self).__init__(*args, **kwargs)
		self.primary_colour = [0.5, 0, 0.5]
		self.secondary_colour = [0.26, 0.28, 0.35]
		self.tertiary_colour = [0, 0, 0]
		self.__page_title = ''

	def generate(self, export_file):
		logger.info("Generating MINIMALIST report for " + str(self.year))
		logger.debug("Saving as " + export_file)
		doc = ImoutoMinimalistTemplate(export_file, self.getLayout(), pagesize=self.page_size, rightMargin=self.right_margin, leftMargin=self.left_margin, topMargin=self.top_margin, bottomMargin=self.bottom_margin)
		report = Year.objects.get(year=self.year)
		doc.multiBuild(self.generate_year_story())

	def getLayout(self):

		def __life_event(canvas, doc):
			canvas.saveState()
			canvas.setFillColorRGB(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2])
			canvas.rect(0, 0, (self.left_margin + (self.content_width / 3.0)), self.page_height, stroke=0, fill=1)
			canvas.restoreState()

		def __event_border(canvas, doc):
			global page_count
			canvas.saveState()
			canvas.setFillColorRGB(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2])
			if doc.page % 2 == 0:
				canvas.rect(0, 0, (self.left_margin + (self.content_width / 3.0)), self.page_height, stroke=0, fill=1)
			else:
				canvas.rect(self.page_width - (self.left_margin + (self.content_width / 3.0)), 0, (self.left_margin + (self.content_width / 3.0)), self.page_height, stroke=0, fill=1)
			canvas.rect(0, (self.content_height + self.bottom_margin), self.page_width, self.top_margin, stroke=0, fill=1)
			canvas.rect(0, 0, self.page_width, self.bottom_margin, stroke=0, fill=1)
			page_count = doc.page
			canvas.restoreState()

		def __half_border(canvas, doc):
			canvas.saveState()
			canvas.setFillColorRGB(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2])
			canvas.rect(0, 0, self.left_margin, self.page_height / 2, stroke=0, fill=1)
			canvas.rect(self.page_width - self.right_margin, 0, self.right_margin, self.page_height / 2, stroke=0, fill=1)
			canvas.rect(0, 0, self.page_width, self.bottom_margin, stroke=0, fill=1)
			canvas.restoreState()

		def __half_page_fill(canvas, doc):
			canvas.saveState()
			canvas.setFillColorRGB(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2])
			canvas.rect(0, 0, self.page_width, self.page_height / 2, stroke=0, fill=1)
			canvas.restoreState()

		def __footer(canvas, doc):
			canvas.saveState()
			canvas.setFont(self.title_font, 12)
			canvas.setFillColorRGB(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2])
			text = str(doc.page)
			if doc.page % 2 == 0:
				canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			else:
				canvas.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			canvas.restoreState()

		def __footer_inverse(canvas, doc):
			canvas.saveState()
			canvas.setFont(self.title_font, 12)
			canvas.setFillColorRGB(1, 1, 1)
			text = str(doc.page)
			if doc.page % 2 == 0:
				canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			else:
				canvas.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 0.5*cm, text)
			canvas.restoreState()

		column_width = (self.content_width / 2) - 6
		return [PageTemplate(id='TitlePage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='titlepage')),
			PageTemplate(id='FullPage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='fullpage'), onPageEnd=__footer_inverse),
			PageTemplate(id='FullPageBlock', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='fullpageblock'), onPage=__half_page_fill, onPageEnd=__footer_inverse),
			PageTemplate(id='LifeEventPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPage=__life_event),
			PageTemplate(id='PeoplePage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='peoplepage'), onPageEnd=__footer),
			PageTemplate(id='EventsPage', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='eventspage'), onPage=__event_border, onPageEnd=__footer_inverse),
			PageTemplate(id='Normal', frames=Frame(self.left_margin, self.bottom_margin, self.content_width, self.content_height, id='normal'), onPageEnd=__footer),
			PageTemplate(id='StatsPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPageEnd=__footer),
			PageTemplate(id='ContentsPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPageEnd=__footer),
			PageTemplate(id='IndexPage', frames=[
				Frame(self.left_margin, self.bottom_margin, column_width, self.content_height, id='col1'),
				Frame((self.left_margin + self.content_width) - column_width, self.bottom_margin, column_width, self.content_height, id='col2')
			], onPageEnd=__footer)]

	def getStyles(self):

		ret = super(ImoutoMinimalistReportStyle, self).getStyles()

		ret['YearTitle'] = ParagraphStyle('YearTitle', parent=ret['Title'], fontName=self.title_font, alignment=1, textTransform='uppercase', fontSize=100, leading=120)
		ret['SectionTitle'] = ParagraphStyle('SectionTitle', parent=ret['Title'], fontName=self.title_font, alignment=1, textTransform='uppercase', fontSize=52, textColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), leading=64)
		ret['SectionSubTitle'] = ParagraphStyle('SectionSubTitle', parent=ret['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', fontSize=28, backColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), textColor='#FFFFFF', leading=32)
		ret['ChartTitle'] = ParagraphStyle('GraphTitle', parent=ret['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), spaceBefore=cm, spaceAfter=0, textColor='#FFFFFF')
		ret['GraphTitle'] = ParagraphStyle('GraphTitle', parent=ret['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), spaceBefore=cm, spaceAfter=0, textColor='#FFFFFF')
		ret['StatsPageTitle'] = ParagraphStyle('StatsPageTitle', parent=ret['Heading1'], fontName=self.title_font, alignment=1)
		ret['LifeEventTitle'] = ParagraphStyle('LifeEventTitle', parent=ret['Heading1'], fontName=self.title_font, alignment=1)
		ret['EventTitle'] = ParagraphStyle('EventTitle', parent=ret['Heading2'], fontName=self.title_font, backColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), textColor='#FFFFFF')
		ret['EventDate'] = ParagraphStyle('EventDate', parent=ret['Normal'], fontName=self.main_font, fontSize=16, leading=20)
		ret['EventText'] = ParagraphStyle('EventText', parent=ret['Normal'], fontName=self.main_font, fontSize=16, leading=18)
		ret['StatisticTitle'] = ParagraphStyle('StatisticTitle', parent=ret['Heading2'], fontName=self.title_font, alignment=1, textTransform='uppercase', backColor=Color(self.primary_colour[0], self.primary_colour[1], self.primary_colour[2], 1), spaceBefore=cm, spaceAfter=0, textColor='#FFFFFF')
		ret['StatisticValue'] = ParagraphStyle('StatisticValue', parent=ret['Heading1'], fontName=self.title_font, alignment=1, spaceBefore=0, spaceAfter=0)
		ret['StatisticDescription'] = ParagraphStyle('StatisticDescription', parent=ret['Normal'], fontName=self.main_font, alignment=1, spaceBefore=0, spaceAfter=1.5*cm, fontSize=16, leading=20)

		return ret

	def generate_month_title(self, month):

		story = []
		styles = self.getStyles()
		story.append(Spacer(10*cm, 10*cm))
		story.append(Paragraph(str(month.name), style=styles['SectionSubTitle']))
		story.append(Paragraph(str(month.year), style=styles['SectionTitle']))
		return story


	def generate_life_event_story(self, event):

		logger.debug("... Generating life event story: " + str(event))

		story = []
		photo_collages = []
		events = []
		styles = self.getStyles()
		column_width = (self.content_width / 2) - 6
		for e in event.subevents().order_by('start_time'):
			for c in e.photo_collages.all():
				photo_collages.append(Image(str(c.image.file), width=18*cm, height=25*cm))
			if ((e.description) or (e.cached_staticmap)):
				events.append(self.event_to_flowable(e))

		if event.cover_photo:
			tf = NamedTemporaryFile(delete=False)
			im = event.cover_photo.thumbnail(200)
			im.save(tf, format='JPEG')
			story.append(Image(str(tf.name), width=column_width, height=column_width))

		story.append(FrameBreak())
		story.append(Paragraph(event.caption, style=styles['LifeEventTitle']))
		story.append(Paragraph(self.event_to_indices(event) + event.description_html(), style=styles['EventText']))
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

	def event_to_flowable(self, event):

		ret = None
		column_width = (self.content_width / 2) - 6
		html = self.event_to_indices(event) + event.description_html()
		styles = self.getStyles()
		right_column = Spacer(width=column_width, height=column_width)
		if event.cover_photo:
			tf = NamedTemporaryFile(delete=False)
			im = event.cover_photo.thumbnail(200)
			im.save(tf, format='JPEG')
			if os.path.exists(str(tf.name)):
				right_column = EventImage(str(tf.name), width=column_width, height=column_width)
		elif event.cached_staticmap:
			if os.path.exists(str(event.cached_staticmap.file)):
				right_column = EventImage(str(event.cached_staticmap.file), width=column_width, height=column_width)
		ret = EventTable(
			[
				[
					[Paragraph(event.caption, style=styles['EventTitle']), Paragraph(event.start_time.strftime("%A %-d %B"), style=styles['EventDate']), Paragraph(html, style=styles['EventText'])], 
					[right_column]
				]
			], colWidths=[None, column_width], minRowHeights=[column_width + cm], splitInRow=1, spaceAfter=cm, style=[('VALIGN', (0, 0), (-1, -1), 'TOP')])
		return ret
