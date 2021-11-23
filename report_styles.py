from fpdf import FPDF
from tempfile import NamedTemporaryFile
from .models import Photo, Person
import os, urllib.request

class DefaultReport(FPDF):

	def __init__(self):
		super().__init__(orientation='P', unit='mm', format='A4')
		self.set_author('Imouto')
		self.set_creator('Imouto')
		self.set_font('Times', '', 14)
		self.__temp = []

	def __new_page(self):
		try:
			y = self.get_y()
		except AttributeError:
			y = 200
		if y >= 11:
			self.add_page()

	def __person_thumbnail(self, image):
		person = None
		for p in Person.objects.all():
			if not(p.image):
				continue
			if not(p.image.path in image):
				continue
			person = p
			break
		if person is None:
			return image
		tf = NamedTemporaryFile(mode='wb', suffix='.jpg')
		im = person.thumbnail(480)
		im.save(tf.name, "JPEG")
		self.__temp.append(tf)
		return tf.name

	def __cache_image(self, image):
		if os.path.exists(image):
			return image
		if '://' in str(image): # ie it's a URL
			parse = str(image).split('.')
			ext = '.' + parse[-1:]
			if len(ext) == 1:
				ext = None
			if len(ext) > 5:
				ext = None
			tf = NamedTemporaryFile(mode='wb', suffix=ext)
			with urllib.request.urlopen(image) as rc:
				tf.write(rc.read())
			self.__temp.append(tf)
			return tf.name
		try:
			photo = Photo.objects.get(id=image)
		except:
			photo = None
		if photo is None:
			return ''
		tf = NamedTemporaryFile(mode='wb', suffix='.jpg')
		im = photo.image()
		im.save(tf.name, "JPEG")
		self.__temp.append(tf)
		return tf.name

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
				self.image(self.__cache_image(rows[i]['image']), image_left, image_top, (actual_width / 2) - 10)
		self.set_font('Times', '', 14)

	def add_image_page(self, image, format='PNG'):
		self.__new_page()
		self.image(self.__cache_image(image), 5.0, 5.0, 200.0, 287.0, type=format)
		self.set_xy(200.0, 150.0)
		self.set_font('Arial', '', 14)

	def add_feature_page(self, title, description, image='', format='JPG'):
		self.__new_page()
		self.set_auto_page_break(False, 0)
		if image != '':
			self.image(self.__cache_image(image), 0.0, 0.0, 210.0, type=format)
		self.set_xy(0, 150)
		self.set_fill_color(255, 255, 255)
		self.cell(210.0, 150, '', 0, 0, '', True)
		self.set_xy(10, 155)
		self.set_auto_page_break(True, 2)
		self.set_font('Arial', 'B', 18)
		self.cell(190, 11, title, 0, 1, 'C', False)
		self.set_font('Times', '', 12)
		self.multi_cell(190, 6, description, 0, 2, 'L')

	def add_chart_page(self, title, description, data):
		self.__new_page()
		self.set_auto_page_break(False, 0)
		self.set_font('Arial', 'B', 18)
		self.set_xy(10, 10)
		self.cell(190, 11, title, 1, 1, 'C', False)
		self.set_font('Times', '', 12)
		self.multi_cell(190, 6, description, 0, 2, 'L')
		y = self.get_y()
		row_top = y + 5
		for item in data:
			self.set_xy(60, row_top)
			self.set_font('Times', '', 16)
			self.cell(160, 18, item['text'], 0, 1, 'L', False)
			if 'image' in item:
				self.image(self.__person_thumbnail(item['image']), 30, row_top, 18, 18)
			row_top = self.get_y() + 5
		self.set_font('Times', '', 12)

	def add_grid_page(self, title, data):
		self.__new_page()
		self.set_auto_page_break(False, 0)
		self.set_font('Arial', 'B', 18)
		self.set_xy(10, 10)
		self.cell(190, 11, title, 1, 2, 'C', False)
		self.set_font('Times', '', 12)
		cols = 4
		if len(data) < 10:
			cols = 3
			if len(data) < 7:
				cols = 2
		cell_width = int(190 / cols)
		row = 0
		col = 0
		for item in data:
			text = ''
			if 'name' in item:
				text = item['name']
			if 'title' in item:
				text = item['title']
			if 'text' in item:
				text = item['text']
			cell_x = (10 + (col * cell_width))
			cell_y = (26 + (row * cell_width))
			self.set_font('Times', '', 12)
			self.set_xy(cell_x, cell_y)
			self.cell(cell_width, cell_width, '', 0)
			self.set_xy(cell_x, cell_y + (cell_width * 0.1) + (cell_width / 2))
			self.cell(cell_width, (cell_width * 0.25), text, 0, 2, 'C', False)
			if 'image' in item:
				self.image(self.__person_thumbnail(item['image']), cell_x + ((cell_width / 2) - ((cell_width * 0.5) / 2)), cell_y + (cell_width * 0.1), (cell_width / 2), (cell_width / 2))
			col = col + 1
			if col > (cols - 1):
				col = 0
				row = row + 1
		self.set_font('Times', '', 12)
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

