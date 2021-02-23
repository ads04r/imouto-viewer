from fpdf import FPDF

class DefaultReport(FPDF):

	def __init__(self):
		super().__init__(orientation='P', unit='mm', format='A4')
		self.set_author('Imouto')
		self.set_creator('Imouto')
		self.set_font('Times', '', 14)

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
		self.set_font('Times', '', 14)

	def add_image_page(self, image):
		self.add_page()
		self.image(image, 5.0, 5.0, 200.0, 287.0, type='PNG')
		self.set_font('Arial', '', 14)

	def render_event(self, event):
		y = self.get_y()
		if y > 230:
			self.add_page()
			self.set_xy(15.0, 15.0)
			y = self.get_y()
		self.set_font('Arial', 'B', 16)
		self.cell(200, 0, event.caption, 0, 0, 'L')
		self.set_font('Times', '', 12)
		self.set_xy(15, y + 7)
		ds = event.start_time.strftime("%A") + ' '
		ds = ds + (event.start_time.strftime("%d").lstrip('0')) + ' '
		ds = ds + event.start_time.strftime("%B, ")
		time_h = int(event.start_time.strftime("%I"))
		time_h_24 = int(event.start_time.strftime("%H"))
		if time_h == time_h_24:
			ds = ds + str(time_h) + event.start_time.strftime(":%M") + "am"
		else:
			ds = ds + str(time_h) + event.start_time.strftime(":%M") + "pm"
		self.cell(200, 0, ds, 0, 0, 'L')
		self.set_font('Times', '', 14)
		self.set_xy(20, y + 15)
		self.multi_cell(175, 7, event.description, 0, 2, 'L')
		y = self.get_y()
		self.set_xy(15.0, y + 20)

	def add_life_event_page(self, event):
		self.add_page()
		self.set_font('Arial', 'B', 24)
		self.set_xy(5.0, 25.0)
		self.cell(200, 0, event.caption, 0, 0, 'C')
		self.set_font('Times', '', 16)
		self.set_xy(15.0, 40.0)
		self.set_font('Times', '', 14)

		if event.description != '':
			self.multi_cell(180, 7, event.description, 0, 2, 'L')
			y = self.get_y()
			self.set_xy(15.0, y + 20)

		for e in event.subevents():
			if ((e.type != 'event') & (e.description == '')):
				continue
			self.render_event(e)

	def add_stats_category(self, title, properties):
		self.add_page()
		self.set_font('Arial', 'B', 24)
		self.set_xy(5.0, 25.0)
		self.cell(200, 0, title, 0, 0, 'C')
		self.set_font('Times', '', 16)
		self.set_xy(30.0, 40.0)
		for prop in properties:
			y = self.get_y()
			self.set_font('Times', '', 16)
			self.set_xy(15.0, y)
			self.cell(130, 0, str(prop.key), 0, 0, 'L')
			self.set_xy(145.0, y)
			self.cell(40, 0, str(prop.value), 0, 0, 'R')
			self.set_xy(15.0, y)
			if prop.description:
				self.set_font('Times', '', 12)
				self.cell(200, 12, str(prop.description), 0, 0, 'L')
				y = y + 12
			y = y + 16
			self.set_xy(15.0, y)
		self.set_font('Times', '', 14)

