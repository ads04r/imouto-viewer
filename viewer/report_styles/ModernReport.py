from django.conf import settings
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from viewer.models import Photo, Person
import os, urllib.request

class ModernReport(FPDF):

	def __init__(self):
		super().__init__(orientation='P', unit='mm', format='A4')
		self.set_author('Imouto')
		self.set_creator('Imouto')
		self.add_font(family='Hatten', fname=settings.WORDCLOUD_FONT, uni=True)
		self.set_font('Arial', '', 14)
		self.__temp = []

	def header(self):
		pn = int(self.page_no())
		image = os.path.join(settings.MEDIA_ROOT, 'templates', 'green-rocks.png')
		if pn % 2 == 0:
			odd = False
		else:
			odd = True
		self.set_fill_color(39, 53, 131)
		if odd:
			self.set_xy(0, 0)
			self.cell(35, 35, '', 0, 2, 'L', True)
			self.set_xy(35, 0)
			self.image(image, 35, 0, 0, 35)
			self.set_xy(0, 35)
			self.cell(35, 212, '', 0, 2, 'L', True)
		else:
			self.set_xy(0, 0)
			self.image(image, 0, 0, 175, 35)
			self.set_xy(175, 0)
			self.cell(35, 35, '', 0, 2, 'L', True)
			self.set_xy(175, 35)
			self.cell(35, 212, '', 0, 2, 'L', True)

	def footer(self):
		pn = int(self.page_no())
		if pn % 2 == 0:
			odd = False
		else:
			odd = True
		if odd:
			self.set_xy(0, -50)
			self.set_fill_color(39, 53, 131)
			self.cell(35, 50, '', 0, 2, 'L', True)
			self.set_xy(0, -15)
			self.set_fill_color(63, 164, 53)
			self.cell(35, 15, '', 0, 2, 'L', True)
			self.set_xy(35, -15)
			self.set_fill_color(158, 199, 131)
			self.cell(175, 15, '', 0, 2, 'L', True)
		else:
			self.set_xy(175, -50)
			self.set_fill_color(39, 53, 131)
			self.cell(35, 50, '', 0, 2, 'L', True)
			self.set_xy(0, -15)
			self.set_fill_color(158, 199, 131)
			self.cell(175, 15, '', 0, 2, 'L', True)
			self.set_xy(175, -15)
			self.set_fill_color(63, 164, 53)
			self.cell(35, 15, '', 0, 2, 'L', True)

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
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			odd = False
			x = 0
		else:
			odd = True
			x = 35
		self.set_font('Hatten', '', 90)
		self.set_xy(x, 140)
		self.cell(175, 0, title, 0, 2, 'C')
		self.set_font('Hatten', '', 24)
		self.set_xy(x, 165.0)
		self.cell(175, 0, subtitle, 0, 2, 'C')
		self.set_font('Arial', '', 14)

	def add_image_page(self, image, format='PNG', caption=''):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			x = 0
		else:
			x = 35
		if len(caption) > 0:
			self.set_text_color(255, 255, 255)
			self.set_font('Hatten', '', 28)
			self.set_xy(x, 10)
			self.cell(175, 15, caption, 0, 1, 'C', False)
			self.set_text_color(0, 0, 0)
		self.image(self.__cache_image(image), x, 35, 175, 247, type=format)
		self.set_xy(200.0, 150.0)
		self.set_font('Hatten', '', 14)

	def add_feature_page(self, title, description, image='', format='JPG'):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			odd = False
			x = 0
		else:
			odd = True
			x = 35
		self.set_auto_page_break(False, 0)
		self.set_fill_color(0, 0, 0)
		self.set_xy(x, 35)
		self.cell(175, 123, '', 0, 0, '', True)
		if image != '':
			self.image(self.__cache_image(image), x, 35, 175, type=format)
		self.set_xy(x, 158)
		self.cell(175, 124, '', 0, 0, '', True)
		self.set_fill_color(255, 255, 255)
		self.set_xy(x, 163)
		self.set_auto_page_break(True, 2)
		self.set_text_color(255, 255, 255)
		self.set_font('Hatten', '', 22)
		self.cell(175, 12, title, 0, 1, 'C', False)
		self.set_font('Arial', '', 12)
		y = self.get_y()
		self.set_xy(x + 5, y)
		self.multi_cell(165, 6, description, 0, 2, 'L')
		self.set_text_color(0, 0, 0)

	def add_chart_page(self, title, description, data):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			x = 0
		else:
			x = 35
		self.set_auto_page_break(False, 0)
		self.set_text_color(255, 255, 255)
		self.set_font('Hatten', '', 28)
		self.set_xy(x, 10)
		self.cell(175, 15, title, 0, 1, 'C', False)
		self.set_text_color(0, 0, 0)
		self.set_font('Arial', '', 12)
		self.set_xy(x + 5, 40)
		self.multi_cell(165, 6, description, 0, 2, 'L')
		y = self.get_y()
		row_top = y + 5
		for item in data:
			self.set_xy(x + 60, row_top)
			self.set_font('Hatten', '', 16)
			self.cell(160, 18, item['text'], 0, 1, 'L', False)
			if 'image' in item:
				self.image(self.__person_thumbnail(item['image']), 30 + x, row_top, 18, 18)
			row_top = self.get_y() + 4
		self.set_font('Arial', '', 12)

	def add_stats_page(self, title, data):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			x = 0
		else:
			x = 35
		self.set_auto_page_break(False, 0)
		self.set_text_color(255, 255, 255)
		self.set_font('Hatten', '', 28)
		self.set_xy(x, 10)
		self.cell(175, 15, title.title(), 0, 1, 'C', False)
		self.set_text_color(0, 0, 0)
		self.set_font('Arial', '', 12)
		cols = 3
		big_font = 64
		if len(data) < 7:
			cols = 2
			big_font = 96
		cell_width = int(175 / cols)
		row = 0
		col = 0
		for item in data:
			#self.set_xy((x + (col * cell_width)), (35 + (row * cell_width)))
			#self.cell(cell_width, cell_width, '', 1)
			self.set_font('Hatten', '', big_font)
			self.set_xy((x + (col * cell_width)) + 5, (35 + (row * cell_width)) + 5)
			fv = float(item['value'])
			iv = int(fv)
			if (fv - float(iv)) > 0.0:
				sv = f'{fv:,}'
			else:
				sv = f'{iv:,}'
			self.cell(cell_width - 10, cell_width - 10, sv, 0, 0, 'C')
			self.set_font('Hatten', '', 14)
			self.set_xy((x + (col * cell_width)) + 5, (35 + (row * cell_width)) + 5)
			self.cell(cell_width - 10, 10, item['key'], 0, 0, 'C')
			col = col + 1
			if col > (cols - 1):
				col = 0
				row = row + 1
		self.set_font('Arial', '', 12)
		self.set_auto_page_break(True, 2)

	def add_grid_page(self, title, data):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			x = 0
		else:
			x = 35
		self.set_auto_page_break(False, 0)
		self.set_text_color(255, 255, 255)
		self.set_font('Hatten', '', 28)
		self.set_xy(x, 10)
		self.cell(175, 15, title, 0, 1, 'C', False)
		self.set_text_color(0, 0, 0)
		self.set_font('Arial', '', 12)
		cols = 4
		if len(data) < 10:
			cols = 3
			if len(data) < 7:
				cols = 2
		cell_width = int(165 / cols)
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
			cell_x = (x + (col * cell_width) + 10)
			cell_y = (35 + (row * cell_width))
			self.set_font('Arial', '', 12)
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
		self.set_font('Arial', '', 12)
		self.set_auto_page_break(True, 2)

	def add_row_items_page(self, rows):
		self.__new_page()
		pn = int(self.page_no())
		if pn % 2 == 0:
			x = 0
		else:
			x = 35
		self.set_fill_color(0, 0, 0)
		margin_height = 5
		margin_width = 5
		page_height = 240.0
		page_width = 175.0
		row_height = int(page_height / len(rows))
		self.set_fill_color(0, 0, 0)
		self.set_xy(0, 0)
		self.set_auto_page_break(False, 0)
		for i in range(0, len(rows)):
			row_top = 35 + (row_height * i) + margin_height
			actual_y = self.get_y()
			if actual_y > row_top:
				row_top = actual_y
			text_width = page_width - (2 * margin_width)
			if 'image' in rows[i]:
				text_width = ((page_width / 3) * 2) - (2 * margin_width)
			image_left = x + text_width + (margin_width * 2)

			self.set_xy(x + margin_width, row_top)
			self.set_font('Hatten', '', 18)
			self.set_text_color(255, 255, 255)
			self.cell(text_width, 11, rows[i]['title'], 1, 2, 'L', True)

			self.set_xy(x + margin_width, row_top + 11)
			self.set_font('Hatten', '', 14)
			self.set_text_color(0, 0, 0)
			self.cell(text_width, 10, rows[i]['date'], 0, 2, 'L')

			self.set_xy(x + margin_width, row_top + 21)
			self.set_font('Arial', '', 10)
			self.multi_cell(text_width, 5, rows[i]['description'], 0, 2, 'L')

			if 'image' in rows[i]:
				self.image(self.__cache_image(rows[i]['image']), image_left, row_top, (text_width / 2) - margin_width)

		self.set_auto_page_break(True, 2)
		self.set_fill_color(255, 255, 255)
		self.set_font('Arial', '', 14)

