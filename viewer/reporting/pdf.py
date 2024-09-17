from viewer.reporting.styles.basic import ImoutoSampleReportStyle

import logging
logger = logging.getLogger(__name__)

def generate_year_pdf(year, export_file, document_class=ImoutoSampleReportStyle):

	report = document_class(year)
	report.generate(export_file)
