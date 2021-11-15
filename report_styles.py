from fpdf import FPDF
import os

class DefaultReport(FPDF):

	def __init__(self):
		super().__init__(orientation='P', unit='mm', format='A4')
		self.set_author('Imouto')
		self.set_creator('Imouto')
		self.set_font('Times', '', 14)

	def __new_page(self):
		try:
			y = self.get_y()
		except AttributeError:
			y = 200
		if y >= 11:
			self.add_page()

	def add_title_page(self, title, subtitle=''):
		self.set_title(title)
		self.__new_page()
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

	def add_row_items_page(self, rows):
		self.__new_page()
		margin_height = self.get_y()
		margin_width = self.get_x()
		page_height = 300
		page_width = 210
		row_spacing = (int((float(page_height - (4 * margin_height))) / (float(len(rows)))))
		row_height = row_spacing - (margin_height / 2)
		row_width = page_width - (2 * margin_width)
		for i in range(0, len(rows)):
			actual_width = row_width
			actual_y = self.get_y()
			if 'image' in rows[i]:
				actual_width = ((row_width / 3) * 2)
			expected_y = (margin_height * 2) + (i * row_spacing)
			image_top = actual_y
			if expected_y > actual_y:
				self.set_xy(margin_width, expected_y)
				image_top = expected_y
			image_left = actual_width + 20
			self.set_font('Arial', 'B', 18)
			self.cell(actual_width, 11, rows[i]['title'], 1, 2, 'L', False)
			self.set_font('Arial', '', 14)
			self.cell(actual_width, 10, rows[i]['date'], 0, 2, 'L')
			self.set_font('Times', '', 12)
			self.multi_cell(actual_width, 6, rows[i]['description'], 0, 2, 'L')
			if i < (len(rows) - 1):
				self.cell(actual_width, 10, '', 0, 2, 'L')
			if 'image' in rows[i]:
				self.image(rows[i]['image'], image_left, image_top, (actual_width / 2) - 10)
		self.set_font('Times', '', 14)

	def add_image_page(self, image, format='PNG'):
		self.__new_page()
		self.image(image, 5.0, 5.0, 200.0, 287.0, type=format)
		self.set_xy(200.0, 150.0)
		self.set_font('Arial', '', 14)

	def add_feature_page(self, title, description, image='', format='JPG'):
		self.__new_page()
		self.set_auto_page_break(False, 0)
		if image != '':
			self.image(image, 0.0, 0.0, 210.0, type=format)
		self.set_xy(0, 150)
		self.set_fill_color(255, 255, 255)
		self.cell(210.0, 150, '', 0, 0, '', True)
		self.set_xy(10, 155)
		self.set_font('Arial', 'B', 18)
		self.cell(190, 11, title, 0, 1, 'C', False)
		self.set_font('Times', '', 12)
		self.multi_cell(190, 6, description, 0, 2, 'L')
		self.set_auto_page_break(True, 2)

	def add_stats_page(self, title, data):
		self.__new_page()
		self.set_font('Arial', 'B', 18)
		self.set_xy(10, 10)
		self.cell(190, 11, title, 1, 2, 'C', False)
		self.set_font('Times', '', 12)
		cols = 3
		big_font = 64
		if len(data) < 7:
			cols = 2
			big_font = 96
		cell_width = int(190 / cols)
		row = 0
		col = 0
		for item in data:
			self.set_xy((10 + (col * cell_width)), (26 + (row * cell_width)))
			self.cell(cell_width, cell_width, '', 1)
			self.set_font('Arial', 'B', big_font)
			self.set_xy((10 + (col * cell_width)) + 5, (26 + (row * cell_width)) + 5)
			self.cell(cell_width - 10, cell_width - 10, item['value'], 0, 0, 'C')
			self.set_font('Arial', '', 14)
			self.set_xy((10 + (col * cell_width)) + 5, (26 + (row * cell_width)) + 5)
			self.cell(cell_width - 10, 10, item['key'], 0, 0, 'C')
			col = col + 1
			if col > (cols - 1):
				col = 0
				row = row + 1
		self.set_font('Times', '', 12)

# data.append({"category": "photos", "key": "Photos Taken", "value": "2893", "icon": "camera", "description": "Some photos"})
