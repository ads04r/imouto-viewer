from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, Paragraph, ParagraphAndImage, KeepTogether, Table, Image, PageBreak, PageBreakIfNotEmpty, Frame, Spacer
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet as get_stylesheet_template
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from viewer.models.core import Year, Month, Day, Event
from tempfile import NamedTemporaryFile
import random, json, markdown, os

class ImoutoSampleYearTemplate(BaseDocTemplate):

	def __init__(self, filename, **kw):
		BaseDocTemplate.__init__(self, filename, **dict(kw, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm))
		self.addPageTemplates(imouto_sample_layout(self))
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

class ImoutoSampleMonthTemplate(BaseDocTemplate):

	def __init__(self, filename, **kw):
		BaseDocTemplate.__init__(self, filename, **dict(kw, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm))
		self.addPageTemplates(imouto_sample_layout(self))

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

def imouto_sample_layout(doc):

	return [PageTemplate(id='TitlePage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='titlepage')),
		PageTemplate(id='FullPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='fullpage')),
		PageTemplate(id='LifeEventPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='lifeeventpage'), onPageEnd=__imouto_sample_footer),
		PageTemplate(id='PeoplePage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='peoplepage'), onPageEnd=__imouto_sample_footer),
		PageTemplate(id='EventsPage', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='eventspage'), onPageEnd=__imouto_sample_footer),
		PageTemplate(id='Normal', frames=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal'), onPageEnd=__imouto_sample_footer),
		PageTemplate(id='StatsPage', frames=[
			Frame(doc.leftMargin, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col1'),
			Frame(doc.leftMargin + (doc.width / 2) + 6, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col2')
		], onPageEnd=__imouto_sample_footer),
		PageTemplate(id='ContentsPage', frames=[
			Frame(doc.leftMargin, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col1'),
			Frame(doc.leftMargin + (doc.width / 2) + 6, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col2')
		], onPageEnd=__imouto_sample_footer),
		PageTemplate(id='IndexPage', frames=[
			Frame(doc.leftMargin, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col1'),
			Frame(doc.leftMargin + (doc.width / 2) + 6, doc.bottomMargin, (doc.width / 2) - 6, doc.height, id='col2')
		], onPageEnd=__imouto_sample_footer)]

def __imouto_sample_footer(canvas, doc):
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

def getSampleStyleSheet():

	sss = get_stylesheet_template()
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
	ret['ChartTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
	ret['GraphTitle'] = ParagraphStyle('GraphTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
	ret['StatsPageTitle'] = ParagraphStyle('StatsPageTitle', parent=sss['Heading1'], alignment=1)
	ret['LifeEventTitle'] = ParagraphStyle('LifeEventTitle', parent=sss['Heading1'], alignment=1)
	ret['EventTitle'] = ParagraphStyle('EventTitle', parent=sss['Heading2'], backColor='#CFCFCF')
	ret['EventDate'] = ParagraphStyle('EventDate', parent=sss['Normal'])
	ret['EventText'] = ParagraphStyle('EventText', parent=sss['Normal'])
	ret['StatisticTitle'] = ParagraphStyle('StatisticTitle', parent=sss['Heading2'], alignment=1, textTransform='uppercase', backColor='#CFCFCF', spaceBefore=cm, spaceAfter=0)
	ret['StatisticValue'] = ParagraphStyle('StatisticValue', parent=sss['Heading1'], alignment=1, spaceBefore=0, spaceAfter=0)
	ret['StatisticDescription'] = ParagraphStyle('StatisticDescription', parent=sss['Normal'], alignment=1, spaceBefore=0, spaceAfter=1.5*cm)

	return ret

