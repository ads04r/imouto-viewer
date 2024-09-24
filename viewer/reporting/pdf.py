from viewer.reporting.styles.basic import ImoutoBasicReportStyle

import logging
logger = logging.getLogger(__name__)

def generate_year_pdf(year, export_file, document_class=ImoutoBasicReportStyle):

	report = document_class(year)
	report.generate(export_file)
