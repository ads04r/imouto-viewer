from django.db import models
from django.core.files import File
from django.db.models import Count
from PIL import Image
from io import BytesIO
import datetime, pytz, json

def user_thumbnail_upload_location(instance, filename):
    return 'people/' + str(instance.pk) + '/' + filename

def photo_thumbnail_upload_location(instance, filename):
    return 'thumbnails/' + str(instance.pk) + '.jpg'

def location_thumbnail_upload_location(instance, filename):
    return 'places/' + str(instance.uid) + '/' + filename

class WeatherLocation(models.Model):
    id = models.SlugField(max_length=32, primary_key=True)
    lat = models.FloatField()
    lon = models.FloatField()
    label = models.CharField(max_length=64)
    def __str__(self):
        return str(self.label)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'weather location'
        verbose_name_plural = 'weather locations'
        indexes = [
            models.Index(fields=['label'])
        ]

class WeatherReading(models.Model):
    time = models.DateTimeField()
    location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, related_name='readings')
    description = models.CharField(max_length=128, blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    wind_speed = models.FloatField(blank=True, null=True)
    wind_direction = models.IntegerField(blank=True, null=True)
    humidity = models.IntegerField(blank=True, null=True)
    visibility = models.IntegerField(blank=True, null=True)
    def __str__(self):
        return str(self.time) + ' at ' + self.location
    class Meta:
        app_label = 'viewer'
        verbose_name = 'weather reading'
        verbose_name_plural = 'weather readings'

class Location(models.Model):
    uid = models.SlugField(unique=True, max_length=32)
    label = models.CharField(max_length=100)
    full_label = models.CharField(max_length=200, default='')
    description = models.TextField(blank=True, null=True)
    lat = models.FloatField()
    lon = models.FloatField()
    creation_time = models.DateTimeField(blank=True, null=True)
    destruction_time = models.DateTimeField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to=location_thumbnail_upload_location)
    weather_location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, null=True, blank=True)
    def people(self):
        ret = []
        for event in self.events.all():
            for person in event.people.all():
                if person in ret:
                    continue
                ret.append(person)
        return ret
    def geo(self):
        point = {}
        point['type'] = "Point"
        point['coordinates'] = [self.lon, self.lat]
        ret = {}
        ret['type'] = "Feature"
        ret['bbox'] = [self.lon - 0.0025, self.lat - 0.0025, self.lon + 0.0025, self.lat + 0.0025]
        ret['properties'] = {}
        ret['geometry'] = point
        return json.dumps(ret);
    def photo(self):
        im = Image.open(self.image.path)
        return im
    def thumbnail(self, size):
        im = Image.open(self.image.path)
        bbox = im.getbbox()
        w = bbox[2]
        h = bbox[3]
        if h > w:
            ret = im.crop((0, 0, w, w))
        else:
            x = int((w - h) / 2)
            ret = im.crop((x, 0, x + h, h))
        ret = ret.resize((size, size), 1)
        return ret
    def get_property(self, key):
        ret = []
        for prop in LocationProperty.objects.filter(location=self).filter(key=key):
            ret.append(str(prop.value))
        return ret
    def get_properties(self):
        ret = []
        for prop in LocationProperty.objects.filter(location=self):
            value = str(prop.key)
            if value in ret:
                continue
            ret.append(value)
        return ret
    def __str__(self):
        label = self.label
        if self.full_label != '':
            label = self.full_label
        return label
    class Meta:
        app_label = 'viewer'
        verbose_name = 'location'
        verbose_name_plural = 'locations'
        indexes = [
            models.Index(fields=['label']),
            models.Index(fields=['full_label']),
        ]

class LocationProperty(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="properties")
    key = models.SlugField(max_length=32)
    value = models.CharField(max_length=255)
    def __str__(self):
        return str(self.location) + ' - ' + self.key
    class Meta:
        app_label = 'viewer'
        verbose_name = 'location property'
        verbose_name_plural = 'location properties'
        indexes = [
            models.Index(fields=['location']),
            models.Index(fields=['key']),
        ]

class Person(models.Model):
    uid = models.SlugField(primary_key=True, max_length=32)
    given_name = models.CharField(null=True, blank=True, max_length=128)
    family_name = models.CharField(null=True, blank=True, max_length=128)
    nickname = models.CharField(null=True, blank=True, max_length=128)
    birthday = models.DateField(null=True, blank=True)
    image = models.ImageField(blank=True, null=True, upload_to=user_thumbnail_upload_location)
    def name(self):
        label = self.nickname
        if ((label == '') or (label is None)):
            label = self.full_name()
        return label
    def full_name(self):
        label = str(self.given_name) + ' ' + str(self.family_name)
        label = label.strip()
        if label == '':
            label = self.nickname
        return label
    def places(self):
        ret = []
        for event in Event.objects.filter(people=self):
            loc = event.location
            if loc is None:
                continue
            if loc in ret:
                continue
            ret.append(loc)
        return ret
    def photo(self):
        im = Image.open(self.image.path)
        return im
    def thumbnail(self, size):
        im = Image.open(self.image.path)
        bbox = im.getbbox()
        w = bbox[2]
        h = bbox[3]
        if h > w:
            ret = im.crop((0, 0, w, w))
        else:
            x = int((w - h) / 2)
            ret = im.crop((x, 0, x + h, h))
        ret = ret.resize((size, size), 1)
        return ret
    def get_property(self, key):
        ret = []
        for prop in PersonProperty.objects.filter(person=self).filter(key=key):
            ret.append(str(prop.value))
        return ret
    def get_properties(self):
        ret = []
        for prop in PersonProperty.objects.filter(person=self):
            value = str(prop.key)
            if value in ret:
                continue
            ret.append(value)
        return ret
    def get_stats(self):
        ret = {'events': 0, 'photos': 0, 'places': 0}
        ret['events'] = Event.objects.filter(people=self).count()
        ret['photos'] = Photo.objects.filter(people=self).count()
        ret['places'] = len(self.places())
        #try:
        ret['first_met'] = Event.objects.filter(people=self).order_by('start_time')[0].start_time
        #except:
        #    ret['first_met'] = None
        return ret
    def photos(self):
        return Photo.objects.filter(people__in=[self]).order_by('-time')
    def events(self):
        return Event.objects.filter(people=self).order_by('-start_time')
    def __str__(self):
        return self.name()
    class Meta:
        app_label = 'viewer'
        verbose_name = 'person'
        verbose_name_plural = 'people'
        indexes = [
            models.Index(fields=['nickname']),
            models.Index(fields=['given_name', 'family_name']),
        ]

class Photo(models.Model):
    file = models.FileField(max_length=255)
    time = models.DateTimeField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    caption = models.CharField(max_length=255, default='', blank=True)
    people = models.ManyToManyField(Person, through='PersonPhoto')
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.CASCADE, related_name="photos")
    cached_thumbnail = models.ImageField(blank=True, null=True, upload_to=photo_thumbnail_upload_location)
    def image(self):
        im = Image.open(self.file.path)
        if hasattr(im, '_getexif'):
            orientation = 0x0112
            exif = im._getexif()
            if exif is not None:
                if orientation in exif:
                    orientation = exif[orientation]
                    rotations = {
                        3: Image.ROTATE_180,
                        6: Image.ROTATE_270,
                        8: Image.ROTATE_90
                    }
                    if orientation in rotations:
                        im = im.transpose(rotations[orientation])
        return im
    def thumbnail(self, size=200):
        if self.cached_thumbnail:
            im = Image.open(self.cached_thumbnail)
            return im
        im = Image.open(self.file.path)
        if hasattr(im, '_getexif'):
            orientation = 0x0112
            exif = im._getexif()
            if exif is not None:
                if orientation in exif:
                    orientation = exif[orientation]
                    rotations = {
                        3: Image.ROTATE_180,
                        6: Image.ROTATE_270,
                        8: Image.ROTATE_90
                    }
                    if orientation in rotations:
                        im = im.transpose(rotations[orientation])
        bbox = im.getbbox()
        w = bbox[2]
        h = bbox[3]
        if h > w:
            ret = im.crop((0, 0, w, w))
        else:
            x = int((w - h) / 2)
            ret = im.crop((x, 0, x + h, h))
        ret = ret.resize((size, size), 1)
        blob = BytesIO()
        ret.save(blob, 'JPEG')
        self.cached_thumbnail.save(photo_thumbnail_upload_location, File(blob), save=False)
        self.save()
        return ret
    def __str__(self):
        return 'Photo ' + str(self.file.path)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'photo'
        verbose_name_plural = 'photos'

class PersonPhoto(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="photos")
    def __str__(self):
        return str(self.person) + ' in ' + str(self.photo)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'person photo'
        verbose_name_plural = 'person photos'

class RemoteInteraction(models.Model):
    type = models.SlugField(max_length=32)
    time = models.DateTimeField()
    address = models.CharField(max_length=128)
    incoming = models.BooleanField()
    title = models.CharField(max_length=255, default='', blank=True)
    message = models.TextField(default='', blank=True)
    def person(self):
        address = self.address.replace(' ', '')
        try:
            person = PersonProperty.objects.get(value=address).person
        except:
            person = None
        return person
    def __str__(self):
        if self.incoming:
            label = 'Message from ' + str(self.address)
        else:
            label = 'Message to ' + str(self.address)
        return label
    class Meta:
        app_label = 'viewer'
        verbose_name = 'remote interaction'
        verbose_name_plural = 'remote interactions'
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['address']),
            models.Index(fields=['time']),
            models.Index(fields=['title']),
        ]

class PersonProperty(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="properties")
    key = models.SlugField(max_length=32)
    value = models.CharField(max_length=255)
    def __str__(self):
        return str(self.person) + ' - ' + self.key
    class Meta:
        app_label = 'viewer'
        verbose_name = 'person property'
        verbose_name_plural = 'person properties'
        indexes = [
            models.Index(fields=['person']),
            models.Index(fields=['key']),
        ]

class DataReading(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    type = models.SlugField(max_length=32)
    value = models.IntegerField()
    def length(self):
        return((self.end_time - self.start_time).total_seconds())
    def __str__(self):
        return str(self.type) + "/" + str(self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
    class Meta:
        app_label = 'viewer'
        verbose_name = 'data reading'
        verbose_name_plural = 'data readings'
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
            models.Index(fields=['type']),
        ]

class Event(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    type = models.SlugField(max_length=32)
    caption = models.CharField(max_length=255, default='', blank=True)
    description = models.TextField(default='', blank=True)
    people = models.ManyToManyField(Person, through='PersonEvent')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    geo = models.TextField(default='', blank=True)
    def __parse_sleep(self, sleep):
        time_from = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        time_to = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        ret = []
        for item in sleep:
            if item.start_time < time_from:
                time_from = item.start_time
            if item.end_time > time_to:
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
        for item in preproc:
            item.append(int((float(item[1]) / float(total)) * 100.0))
            ret.append(item)
        
        return ret

    def refresh(self):
        for photo in Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time):
            for person in photo.people.all():
                self.people.add(person)
        self.save()
    def subevents(self):
        return Event.objects.filter(start_time__gte=self.start_time).filter(end_time__lte=self.end_time).exclude(id=self.id).order_by('start_time')
    def length(self):
        return((self.end_time - self.start_time).total_seconds())
    def length_string(self):
        s = int((self.end_time - self.start_time).total_seconds())
        m = int(s / 60)
        s = s - (m * 60)
        h = int(m / 60)
        m = m - (h * 60)
        if m == 0 & h == 0:
            return str(s) + ' seconds'
        if h == 0:
            if m < 10 & s > 0:
                return str(m) + ' min, ' + str(s) + ' sec'
            else:
                return str(m) + ' minutes'
        return str(h) + ' hour, ' + str(m) + ' min'
    def photos(self):
        ret = Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time)
        return ret.annotate(num_people=Count('people')).order_by('-num_people')
    def documents(self):
        return([])
    def messages(self, type=''):
        if type == '':
            return RemoteInteraction.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time).order_by('time')
        else:
            return RemoteInteraction.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time).filter(type=type).order_by('time')
    def sms(self):
        messages = self.messages('sms')
        people = []
        for message in messages:
            address = message.address.replace(' ', '')
            if address in people:
                continue
            people.append(address)
        ret = []
        for person in people:
            conversation = []
            for message in messages:
                address = message.address.replace(' ', '')
                if address == person:
                    if len(conversation) > 0:
                        delay = message.time - conversation[-1].time
                        if delay.total_seconds() > (3 * 3600):
                            ret.append(conversation)
                            conversation = []
                    conversation.append(message)
            if len(conversation) > 0:
                ret.append(conversation)
        return sorted(ret, key=lambda item: item[0].time)
    def music(self):
        return MediaEvent.objects.filter(time__gte=self.start_time, time__lte=self.end_time).filter(media__type='music').order_by('time')
    def health(self):
        ret = {}
        heart_total = 0.0
        heart_count = 0.0
        heart_max = 0.0
        heart_csv = []
        step_count = 0
        sleep = []
        if self.length() > 86400:
            eventsearch = DataReading.objects.filter(end_time__gte=self.start_time, start_time__lte=self.end_time).exclude(type='heart-rate')
        else:
            eventsearch = DataReading.objects.filter(end_time__gte=self.start_time, start_time__lte=self.end_time)
        for item in eventsearch:
            if item.type=='heart-rate':
                heart_csv.append(str(item.value))
                heart_total = heart_total + float(item.value)
                heart_count = heart_count + 1.0
                if item.value > heart_max:
                    heart_max = item.value
            if item.type=='step-count':
                step_count = step_count + item.value
            if (item.type=='pebble-app-activity') & (item.value <= 2):
                sleep.append(item)
        if heart_count > 0:
            ret['heartavg'] = int(heart_total / heart_count)
            ret['heartmax'] = int(heart_max)
            ret['heart'] = ','.join(heart_csv)
        if len(sleep) > 0:
            ret['sleep'] = self.__parse_sleep(sleep)
        if step_count > 0:
            ret['steps'] = step_count
        return ret
    def __str__(self):
        if self.caption == '':
            return "Event " + str(self.pk)
        else:
            return self.caption
    class Meta:
        app_label = 'viewer'
        verbose_name = 'event'
        verbose_name_plural = 'events'
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
            models.Index(fields=['type'])
        ]

class PersonEvent(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="events")
    def __str__(self):
        return str(self.person) + ' in ' + str(self.event)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'person event'
        verbose_name_plural = 'person events'

class Media(models.Model):
    type = models.SlugField(max_length=16)
    unique_id = models.SlugField(max_length=128)
    label = models.CharField(max_length=255)

class MediaEvent(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="events")
    time = models.DateTimeField()

class LifeReport(models.Model):
    label = models.CharField(max_length=128)
    type = models.SlugField(max_length=32, default='year')
    style = models.SlugField(max_length=32, default='default')
    people = models.ManyToManyField(Person, through='ReportPeople')
    locations = models.ManyToManyField(Location, through='ReportLocations')
    events = models.ManyToManyField(Event, through='ReportEvents')
    def __str__(self):
        return self.label
    class Meta:
        app_label = 'viewer'
        verbose_name = 'life report'
        verbose_name_plural = 'life reports'

class LifeReportProperties(models.Model):
    report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
    key = models.CharField(max_length=128)
    value = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    def __str__(self):
        return str(self.report) + ' - ' + self.key
    class Meta:
        app_label = 'viewer'
        verbose_name = 'life report property'
        verbose_name_plural = 'life report properties'
        indexes = [
            models.Index(fields=['report']),
            models.Index(fields=['key']),
        ]

class ReportPeople(models.Model):
    report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="reports")
    comment = models.TextField(null=True, blank=True)
    def __str__(self):
        return str(self.person) + ' in ' + str(self.report)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'report person'
        verbose_name_plural = 'report people'

class ReportLocations(models.Model):
    report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="reports")
    comment = models.TextField(null=True, blank=True)
    def __str__(self):
        return str(self.location) + ' in ' + str(self.report)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'report location'
        verbose_name_plural = 'report locations'

class ReportEvents(models.Model):
    report = models.ForeignKey(LifeReport, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reports")
    comment = models.TextField(null=True, blank=True)
    def __str__(self):
        return str(self.event) + ' in ' + str(self.report)
    class Meta:
        app_label = 'viewer'
        verbose_name = 'report event'
        verbose_name_plural = 'report events'
