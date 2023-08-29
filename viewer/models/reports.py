from django.db import models
from django.core.files import File
from django.db.models import Field, F
from PIL import Image
from io import BytesIO

from viewer.models.core import LifeReport

from viewer.staticcharts import generate_pie_chart, generate_donut_chart
from viewer.functions.file_uploads import *

import random, datetime, pytz, json, markdown, re, os, urllib.request

class LifeReportProperties(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='properties')
	key = models.CharField(max_length=128)
	value = models.CharField(max_length=255)
	category = models.SlugField(max_length=32, default='')
	icon = models.SlugField(max_length=64, default='bar-chart')
	description = models.TextField(null=True, blank=True)
	def __str__(self):
		return str(self.report) + ' - ' + self.key
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		return {'category': self.category, 'key': self.key, 'value': self.value, 'icon': self.icon, 'description': self.description}
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report property'
		verbose_name_plural = 'life report properties'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['key']),
		]

class LifeReportGraph(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='graphs')
	key = models.CharField(max_length=128)
	data = models.TextField(default='', blank=True)
	category = models.SlugField(max_length=32, default='')
	type = models.SlugField(max_length=16, default='bar')
	icon = models.SlugField(max_length=64, default='bar-chart')
	cached_image = models.ImageField(blank=True, null=True, upload_to=report_graph_upload_location)
	description = models.TextField(null=True, blank=True)
	def image(self, w=640, h=640):
		if ((w == 640) & (h == 640)):
			if self.cached_image:
				im = Image.open(self.cached_image)
				return im
		data = json.loads(self.data)
		ret = None
		if self.type == 'pie':
			ret = generate_pie_chart(data, w, h)
		if self.type == 'donut':
			ret = generate_donut_chart(data, w, h)
		if ret is None:
			return False
		if ((w == 640) & (h == 640)):
			blob = BytesIO()
			ret.save(blob, 'PNG')
			self.cached_image.save(report_graph_upload_location, File(blob), save=False)
			self.save()
		return ret
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		if not self.cached_image:
			im = self.image()
		return {'category': self.category, 'name': self.key, 'image': self.cached_image.path}
	def __str__(self):
		return str(self.report) + ' - ' + self.key
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report graph'
		verbose_name_plural = 'life report graphs'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['type']),
			models.Index(fields=['key']),
		]

class LifeReportChart(models.Model):
	report = models.ForeignKey(LifeReport, on_delete=models.CASCADE, related_name='charts')
	text = models.CharField(max_length=128)
	category = models.SlugField(max_length=32, default='')
	data = models.TextField(default='[]')
	description = models.TextField(null=True, blank=True)
	def to_dict(self):
		"""
		Returns the contents of this object as a dictionary of standard values, which can be serialised and output as JSON.

		:return: The properties of the object as a dict
		:rtype: dict
		"""
		return json.loads(self.data)
	def __str__(self):
		return str(self.report) + ' - ' + self.text
	class Meta:
		app_label = 'viewer'
		verbose_name = 'life report chart'
		verbose_name_plural = 'life report charts'
		indexes = [
			models.Index(fields=['report']),
			models.Index(fields=['text']),
		]

