from django.db import models
from PIL import Image
import datetime, pytz

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

class Person(models.Model):
    uid = models.SlugField(primary_key=True, max_length=32)
    given_name = models.CharField(null=True, blank=True, max_length=128)
    family_name = models.CharField(null=True, blank=True, max_length=128)
    nickname = models.CharField(null=True, blank=True, max_length=128)
    birthday = models.DateField(null=True, blank=True)
    image = models.ImageField(blank=True, null=True)
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
            ret = im.crop((x, 0, h, h))
        ret = ret.resize((size, size), 1)
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
    file = models.FileField()
    time = models.DateTimeField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    caption = models.CharField(max_length=255, default='', blank=True)
    people = models.ManyToManyField(Person, through='PersonPhoto')
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.CASCADE, related_name="photos")
    def thumbnail(self, size):
        im = Image.open(self.file.path)
        bbox = im.getbbox()
        w = bbox[2]
        h = bbox[3]
        if h > w:
            ret = im.crop((0, 0, w, w))
        else:
            x = int((w - h) / 2)
            ret = im.crop((x, 0, h, h))
        ret = ret.resize((size, size), 1)
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
    def length(self):
        return((self.end_time - self.start_time).total_seconds())
    def photos(self):
        return(Photo.objects.filter(time__gte=self.start_time).filter(time__lte=self.end_time))
    def documents(self):
        return([]);
    def messages(self):
        return([]);
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
