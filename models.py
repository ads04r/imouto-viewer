from django.db import models
from django.core.files import File
from django.db.models import Count
from PIL import Image
from io import BytesIO
import datetime, pytz, json

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
    image = models.ImageField(blank=True, null=True)
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

def user_thumbnail_upload_location(instance, filename):
    return 'people/' + str(instance.pk) + '/' + filename

def photo_thumbnail_upload_location(instance, filename):
    return 'thumbnails/' + str(instance.pk) + '.jpg'

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
        ret = []
        for event in MediaEvent.objects.filter(time__gte=self.start_time, time__lte=self.end_time):
            if event.media.type=='music':
                ret.append(event)
        return ret
    def health(self):
        ret = {}
        for item in DataReading.objects.filter(end_time__gte=self.start_time).filter(start_time__lte=self.end_time):
            if item.type=='step-count':
                if 'steps' in ret:
                    ret['steps'] = ret['steps'] + item.value
                else:
                    ret['steps'] = item.value
            if item.type=='pebble-app-activity' & item.value <= 2:
                if not('sleep' in ret):
                    ret['sleep'] = []
                ret['sleep'].append(item)
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
