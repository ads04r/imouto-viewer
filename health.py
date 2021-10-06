import datetime, pytz, json, random, urllib.request, re
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField, fields
from django.conf import settings

def parse_sleep(sleep):

    time_from = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    time_to = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
    ret = []
    for item in sleep:
        if item.start_time < time_from:
            time_from = item.start_time
        if item.end_time > time_to:
            if item.value == 0:
                continue
            time_to = item.end_time
    dts = int(time_from.timestamp())
    dte = int(time_to.timestamp())
    mins = int((dte - dts) / 60)
    lastval = -1
    ct = 0
    total = 0
    for i in range(0, mins):
        time_i = time_from + datetime.timedelta(minutes=i)
        v = 0
        for item in sleep:
            if item.value > v:
                if ((item.start_time <= time_i) & (time_i <= item.end_time)):
                    v = item.value
        if lastval == v:
            ct = ct + 1
        else:
            if lastval > -1:
                block = [lastval, ct]
                total = total + ct
                ret.append(block)
            ct = 0
            lastval = v
    if ct > 0:
        block = [lastval, ct]
        total = total + ct
        ret.append(block)

    preproc = ret
    ret = []
    inc_total = 0
    for item in preproc:
        new_value = int(( (float(item[1])) / (float(total)) ) * 100.0)
        if len(ret) == (len(preproc) - 1):
            item.append(100 - inc_total)
        else:
            item.append(new_value)
            inc_total = inc_total + new_value
        ret.append(item)

    if time_from > time_to:
        return {'data': ret}

    return {'start': time_from.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S%z"), 'end': time_to.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S%z"), 'start_friendly': time_from.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lower().lstrip('0'), 'end_friendly': time_to.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime("%I:%M%p").lower().lstrip('0'), 'data': ret}

