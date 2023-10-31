from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
import random, datetime, pytz, json, markdown, re, os

def generate_pie_chart(data, w=640, h=640, colours=None, legend=True, font_path=None):
	return __generate_radial_chart(data, 'pie', w, h, colours, legend, font_path)

def generate_donut_chart(data, w=640, h=640, colours=None, legend=True, font_path=None):
	return __generate_radial_chart(data, 'donut', w, h, colours, legend, font_path)

def __generate_radial_chart(data, type, w=640, h=640, slice_colours=None, legend=True, font_path=None):

	full_size = h
	if w < full_size:
		full_size = w
	size = int(float(full_size) * 0.95)
	y = int((float(h) / 2.0) - (float(size) / 2.0))
	y_offset = 0
	if legend:
		size = int((float(size) / 3.0) * 2.0)
		y_offset = int((float(h) / 2.0) - (float(size) / 2.0)) - y
	hub_size = size / 2
	x = int((float(w) / 2.0) - (float(size) / 2.0))
	hx = int((float(w) / 2.0) - (float(hub_size) / 2.0))
	hy = int((float(h) / 2.0) - (float(hub_size) / 2.0)) - y_offset
	legend_y = y + size + 10

	im = Image.new('RGB', (w, h), color='white')
	colours = ['#3F3F3F', '#7F7F7F', '#CFCFCF']
	if not(slice_colours is None):
		colours = slice_colours
	values = data[1]
	ttl = 0.0
	for value in values:
		ttl = ttl + float(value)
	xer = 360.0 / ttl
	inc = 0.0
	i = 0
	im0 = ImageDraw.Draw(im)
	im0.pieslice([(x, y), (x + size, y + size)], start=0, end=360, fill='#000000', outline='#000000')
	if font_path is None:
		font = ImageFont.truetype(font=settings.DEFAULT_FONT, size=30)
	else:
		font = ImageFont.truetype(font=font_path, size=30)
	for value in values:
		colour = colours.pop(0)
		colours.append(colour)
		i = i + 1
		st = int(inc)
		ed = int(inc + (float(value) * xer))
		if i == len(values):
			ed = 360
		im1 = ImageDraw.Draw(im)
		im1.pieslice([(x + 5, y + 5), (x + size - 5, y + size - 5)], start=st, end=ed, fill=colour, outline='#000000')
		inc = float(ed)
		if legend:
			im1.rectangle([(x + 5, legend_y + (i * 35)), (x + 30, legend_y + (i * 35) + 25)], fill=colour, outline='#000000')
			im1.text((x + 40, legend_y + (i * 35) - 5), data[0][i - 1], fill='#000000', font=font)
	if type == 'donut':
		im0 = ImageDraw.Draw(im)
		im0.pieslice([(hx, hy), (hx + hub_size, hy + hub_size)], start=0, end=360, fill='#000000', outline='#000000')
		im0.pieslice([(hx + 5, hy + 5), (hx + hub_size - 5, hy + hub_size - 5)], start=0, end=360, fill='#FFFFFF', outline='#FFFFFF')
	return im
