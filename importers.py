import django, os, csv, socket, json, urllib, urllib.request, re, random, glob, sys, PIL.Image, exifread
import datetime, pytz, pymysql, math
from django.conf import settings
from xml.dom import minidom
from fitparse import FitFile
from tzlocal import get_localzone

from viewer.models import *

def import_fit(parseable_fit_input):

    data = []
    fit = FitFile(parseable_fit_input)
    tz = get_localzone()
    tz = pytz.UTC
    for record in fit.get_messages('record'):
        item = {}
        for recitem in record:
            k = recitem.name
            if ((k != 'heart_rate') & (k != 'timestamp') & (k != 'cadence')):
                continue
            v = {}
            v['value'] = recitem.value
            v['units'] = recitem.units
            if ((v['units'] == 'semicircles') & (not(v['value'] is None))):
                v['value'] = float(v['value']) * ( 180 / math.pow(2, 31) )
                v['units'] = 'degrees'
            item[k] = v
        if item['timestamp']['value'].tzinfo is None or item['timestamp']['value'].utcoffset(item['timestamp']['value']) is None:
            item['timestamp']['value'] = tz.localize(item['timestamp']['value'])
            item['timestamp']['value'] = item['timestamp']['value'].replace(tzinfo=pytz.utc) - item['timestamp']['value'].utcoffset() # I like everything in UTC. Bite me.
        newitem = {}
        newitem['date'] = item['timestamp']['value']
        if 'heart_rate' in item:
            newitem['heart'] = item['heart_rate']['value']
        if 'cadence' in item:
            newitem['cadence'] = item['cadence']['value']
        newitem['length'] = 1
        if len(data) > 0:
            lastitem = data[-1]
            lastitem['length'] = int((newitem['date'] - lastitem['date']).total_seconds())
            data[-1] = lastitem
        data.append(newitem)

    for item in data:

        dts = item['date']
        dte = item['date'] + datetime.timedelta(seconds=item['length'])

        if 'heart' in item:
            if not(item['heart'] is None):
                try:
                    event = DataReading.objects.get(start_time=dts, end_time=dte, type='heart-rate')
                except:
                    event = DataReading(start_time=dts, end_time=dte, type='heart-rate', value=item['heart'])
                    event.save()

        if 'cadence' in item:
            if not(item['cadence'] is None):
                try:
                    event = DataReading.objects.get(start_time=dts, end_time=dte, type='cadence')
                except:
                    event = DataReading(start_time=dts, end_time=dte, type='cadence', value=item['cadence'])
                    event.save()

