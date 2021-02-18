from fpdf import FPDF

class DefaultReport(FPDF):

	def __init__(self):
		super().__init__(orientation='P', unit='mm', format='A4')
		self.set_author('Imouto')
		self.set_creator('Imouto')
		self.set_font('Arial', '', 14)

	def add_title_page(self, title, subtitle=''):
		self.set_title(title)
		self.add_page()
		self.set_line_width(0.0)
		self.line(5.0, 5.0, 205.0, 5.0)
		self.line(5.0, 292.0, 205.0, 292.0)
		self.line(5.0, 5.0, 5.0, 292.0)
		self.line(205.0, 5.0, 205.0, 292.0)
		self.set_font('Arial', 'B', 90)
		self.set_xy(5.0, 125.0)
		self.cell(200, 0, title, 0, 2, 'C')
		self.set_font('Arial', 'B', 24)
		self.set_xy(5.0, 150.0)
		self.cell(200, 0, subtitle, 0, 2, 'C')
		self.set_font('Arial', '', 14)

	def add_image_page(self, image):
		self.add_page()
		self.image(image, 5.0, 5.0, 200.0, 287.0, type='PNG')
		self.set_font('Arial', '', 14)

	def add_stats_category(self, title, properties):
		self.add_page()
		self.set_font('Arial', 'B', 24)
		self.set_xy(5.0, 25.0)
		self.cell(200, 0, title, 0, 0, 'C')
		self.set_font('Arial', '', 16)
		self.set_xy(30.0, 40.0)
		for prop in properties:
			y = self.get_y()
			self.set_font('Arial', '', 16)
			self.set_xy(15.0, y)
			self.cell(130, 0, str(prop.key), 0, 0, 'L')
			self.set_xy(145.0, y)
			self.cell(40, 0, str(prop.value), 0, 0, 'R')
			self.set_xy(15.0, y)
			if prop.description:
				self.set_font('Arial', '', 12)
				self.cell(200, 12, str(prop.description), 0, 0, 'L')
				y = y + 12
			y = y + 16
			self.set_xy(15.0, y)
		self.set_font('Arial', '', 14)

