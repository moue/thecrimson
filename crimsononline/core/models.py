from hashlib import md5
from random import randint
from os.path import splitext, exists, split, join
from datetime import datetime, time
from re import compile, match
from string import letters, digits
from PIL import Image as pilImage
from django.conf import settings
from django.db import models
from django.db.models import permalink, Q
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.localflavor.us.models import PhoneNumberField
from django.core.cache import cache
from django.template.defaultfilters import slugify, truncatewords
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

SAFE_CHARS = letters + digits
def filter_string(allowed_chars, str):
    return ''.join([c for c in str if c in allowed_chars])


class ContentGenericManager(models.Manager):
    def type(self, model):
        """takes a model and returns a queryset with all of the 
        ContentGenerics of that contenttype"""
        return self.get_query_set().filter(
            content_type=ContentType.objects.get_for_model(model)
        )
        
    @property
    def recent(self):
        return self.get_query_set() \
            .exclude(issue__web_publish_date__gt=datetime.now()) \
            .order_by('-issue__issue_date', 'priority')


class ContentGeneric(models.Model):
    """
    Facilitates generic relationships between content.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    contributors = models.ManyToManyField('Contributor', 
        null=True, related_name='content')
    tags = models.ManyToManyField('Tag', null=True, related_name='content')
    issue = models.ForeignKey('Issue', null=True, related_name='content')
    section = models.ForeignKey('Section', null=True, related_name='content')
    priority = models.IntegerField(default=0)
    
    objects = ContentGenericManager()
    
    class Meta:
        unique_together = (('content_type', 'object_id',),)
    
    def __unicode__(self):
        return str(self.content_object)
    


class Content(models.Model):
    """
    Has some content rendering functions.
    """
    
    class Meta:
        abstract = True
    
    def _get_contributors(self):
        return self.generic.contributors
    def _set_contributors(self, value):
        self.generic.contributors = value
    contributors = property(_get_contributors, _set_contributors)
    
    def _get_tags(self):
        return self.generic.tags
    def _set_tags(self, value):
        self.generic.tags = value
    tags = property(_get_tags, _set_tags)
    
    def _get_issue(self):
        return self.generic.issue
    def _set_issue(self, value):
        self.generic.issue = value
    issue = property(_get_issue, _set_issue)
    
    def _get_section(self):
        return self.generic.section
    def _set_section(self, value):
        self.generic.section = value
    section = property(_get_section, _set_section)
    
    def _get_priority(self):
        return self.generic.priority
    def _set_priority(self, value):
        self.generic.priority = value
    priority = property(_get_priority, _set_priority)
    
    generic = models.ForeignKey(ContentGeneric, null=True,
        related_name="%(class)s_generic_related")
    
    def _render(self, method, context={}):
        """
        renders in different ways, depending on method
        
        method could be something like, 'admin' or 'search'
        
        use context to inject extra variables into the template
        """
        name = self._meta.object_name.lower()
        templ = 'models/%s/%s.html' % (name, method)
        context.update({name: self, 'class': name})
        # below, maybe instead of name:, have 'obj':
        return mark_safe(render_to_string(templ, context))
    
    @classmethod
    def find_by_date(cls, start, end):
        """
        returns a queryset
        """
        start, end = start.date(), end.date()
        lookup = cls._meta.get_latest_by
        q = {lookup + '__gte': start, lookup + '__lte': end}
        return cls.objects.filter(**q).order_by('-' + lookup)
    
    def save(self, *args, **kwargs):
        # generate a pk if self doesn't have one
        if not self.pk:
            super(Content, self).save(*args, **kwargs)
            kwargs['force_insert'] = False
        # create a ContentGeneric obj
        if not self.generic:
            r = ContentGeneric(content_object=self)
            r.save()
            self.generic = r
        else:
            self.generic.save()
        return super(Content, self).save(*args, **kwargs)
    


class Tag(models.Model):
    """
    A word or phrase used to classify or describe some content.
    
    # A bit of setup
    >>> from django.db import IntegrityError
    
    # Create some tags
    >>> tag1 = Tag.objects.create(text='potato')
    >>> tag2 = Tag.objects.create(text='not potato')
    
    # No duplicate tags
    >>> try:
    ...     tag3 = Tag.objects.create(text='potato')
    ... except IntegrityError:
    ...     print "caught"
    ... 
    caught
    
    # __unicode__
    >>> str(tag1)
    'potato'
    """
    
    text = models.CharField(blank=False, max_length=25, unique=True,
        help_text='Tags can contain letters and spaces')
    
    def __unicode__(self):
        return self.text
    
    @permalink
    def get_absolute_url(self):
        return ('core_tag', [self.text])
    


class Board(models.Model):
    """
    Organizational unit of the Crimson
    
    # create a Board
    >>> b = Board.objects.create(name='biz')
    
    # stupidest test ever
    >>> b.name
    'biz'
    """
    name = models.CharField(blank=False, null=False, max_length=20)
    group = models.ForeignKey(Group, null=True, blank=True)
    
    def __unicode__(self):
        return self.name



def contrib_pic_path(instance, filename):
    ext = splitext(filename)[1]
    name = '%s_%s_%s' % \
        (instance.first_name, instance.middle_initial, instance.last_name)
    return 'photos/contrib_pics/' + name + ext
    
    
class Contributor(models.Model):
    """
    Someone who contributes to the Crimson, 
    like a staff writer, a photographer, or a guest writer.
    
    # Create a contributor
    >>> c = Contributor(first_name='Dan', middle_initial='C',last_name='Carroll')
    
    # Test the unicode string
    >>> str(c)
    'Dan C. Carroll'
    
    # Default is active
    >>> c.is_active
    True
    """
    user = models.ForeignKey(
        "CrimsonUser", verbose_name='web user', unique=True, blank=True, 
        null=True, limit_choices_to={'is_active': True},
    )
    first_name = models.CharField(blank=False, null=True, max_length=70)
    last_name = models.CharField(blank=False, null=True, max_length=100)
    middle_initial = models.CharField(blank=True, null=True, max_length=1)
    created_on = models.DateField(auto_now_add=True)
    type = models.CharField(blank=True, null=True, max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)
    board_number = models.IntegerField(
        blank=True, null=True, help_text='Eg: 136')
    boards = models.ManyToManyField(Board, blank=True, null=True)
    class_of = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True,
        help_text='This should be true for anyone who could possibly still ' \
                    'write for The Crimson, including guest writers.')
    profile_text = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(blank=True, null=True, 
        upload_to=contrib_pic_path)
    
    def __unicode__(self):
        if self.middle_initial == None or self.middle_initial == '':
            m = ''
        else:
            m = ' ' + self.middle_initial + '.'
        return '%s%s %s' % (self.first_name, m, self.last_name)
        
    def __setattr__(self, name, value):
        # hash the huid before storing it; but actually don't
        #if name == 'huid_hash' and value != None:
        #    value = md5(value).digest()
        return super(Contributor, self).__setattr__(name, value)
    
    @permalink
    def get_absolute_url(self):
        return ('core_writer_profile', 
            [str(self.id), self.first_name, self.middle_initial, self.last_name])


class Section(models.Model):
    """
    Eg: News, Sports, etc.
    
    # create some Sections
    >>> l = ['news', 'opinion', 'sports', 'fm']
    >>> for s in l:
    ...     a = Section.objects.create(name=s)
    
    # all() should return all of them
    >>> things = Section.all()
    >>> names = [t.name for t in things]
    >>> for s in l:
    ...     assert s in names, True
    
    # all()'s cache should be inaccurate
    >>> Section.objects.create(name='arts')
    <Section: arts>
    >>> things = Section.all()
    >>> 'arts' in [t.name for t in things]
    False
    """
    
    name = models.CharField(blank=False, max_length=50)
    audiodizer_id = models.IntegerField(blank=True, null=True)
    
    @staticmethod
    def all():
        # cache won't be up to date, but that's fine. 
        #   sections should almost never change
        a = cache.get('sections_all')
        if a is None:
            a = Section.objects.all()[:]
            cache.set('sections_all', a, 1000000)
        return a
    
    def __unicode__(self):
        return self.name


class LiveIssueManager(models.Manager):
    """
    Only returns Issues which are published / unpublished
    
    Arguments
    live:   True => only live objects
            False => no live objects
            None => all objects
    """
    def __init__(self, *args, **kwargs):
        self.live = kwargs.pop('live', None)
        return super(LiveIssueManager, self).__init__(*args, **kwargs)
    
    def get_query_set(self):
        if self.live is None:
            return super(LiveIssueManager, self).get_query_set()
        elif self.live:
            q = Q(web_publish_date__lte=datetime.now())
        else:
            q = Q(web_publish_date__gt=datetime.now())
        return super(LiveIssueManager, self).get_query_set() \
            .filter(q)

class SpecialIssueManager(LiveIssueManager):
    """
    Only returns named issues
    """
    def get_query_set(self):
        return super(SpecialIssueManager, self).get_query_set() \
            .exclude(Q(special_issue_name="") | Q(special_issue_name=None))

class DailyIssueManager(LiveIssueManager):
    """
    Only returns unnamed issues
    """
    def get_query_set(self):
        return super(DailyIssueManager, self).get_query_set() \
            .filter(Q(special_issue_name="") | Q(special_issue_name=None))

class IssueManager(models.Manager):
    
    LIVE = Q(web_publish_date__lte=datetime.now())
    DAILY = Q(special_issue_name="") | Q(special_issue_name=None)
    
    @property
    def live(self):
        return self.get_query_set().filter(IssueManager.LIVE)
    
    @property
    def special(self):
        return self.get_query_set().exclude(IssueManager.DAILY)
    
    @property
    def daily(self):
        return self.get_query_set().filter(IssueManager.DAILY)
    
    @property
    def live_daily(self):
        return self.daily.filter(IssueManager.LIVE)
    
    @property
    def live_special(self):
        return self.special.filter(IssueManager.LIVE)
    


class Issue(models.Model):
    """
    A set of content (articles, photos) for a particular date.
    
    Special issues should NEVER be displayed by default on the index.
    They should be displayed via content modules or special redirects.
    
    # Clear out the fixture preloaded issues
    >>> a = [i.delete() for i in Issue.objects.all()]
    
    # Create some issues
    >>> from datetime import datetime, timedelta
    >>> deltas = [timedelta(days=i) for i in range(-5, 6) if i]
    >>> now = datetime.now()
    >>> for d in deltas:
    ...     a = Issue.objects.create(issue_date=now+d)
    
    # make some of them special
    >>> i1 = Issue.objects.get(pk=1)
    >>> i1.special_issue_name = "Commencement 2008"
    >>> i1.save()
    >>> i2 = Issue.objects.get(pk=6)
    >>> i2.special_issue_name = "Election 2008"
    >>> i2.save()
    
    # managers
    >>> Issue.objects.all().count()
    10
    >>> Issue.objects.special.all().count()
    2
    >>> Issue.objects.daily.all().count()
    8
    >>> Issue.objects.live.all().count()
    5
    >>> Issue.objects.live_special.all().count()
    1
    >>> Issue.objects.live_daily.all().count()
    4
    
    # set_as_current and get_current
    >>> i3 = Issue.objects.get(pk=5)
    >>> i3.set_as_current()
    >>> assert Issue.get_current().issue_date, i2.issue_date
    """
    
    special_issue_name = models.CharField(blank=True, null=True,
        help_text="Leave this blank for daily issues!!!", max_length=100)
    web_publish_date = models.DateTimeField(null=True,
        blank=False, help_text='When this issue goes live (on the web).')
    issue_date = models.DateField(
        blank=False, help_text='Corresponds with date of print edition.')
    comments = models.TextField(
        blank=True, null=True, help_text='Notes about this issue.')
    
    objects = IssueManager()
    
    @staticmethod
    def get_current():
        """gets current issue from cache"""
        i = cache.get('current_issue')
        if not i:
            i = Issue.objects.latest('issue_date')
            i.set_as_current()
        return i
    
    def save(self, *args, **kwargs):
        # web publish date is 6 am on the issue date
        if self.web_publish_date is None:
            self.web_publish_date = datetime.combine(self.issue_date, time(6))
        return super(Issue, self).save(*args, **kwargs)
    
    def set_as_current(self, timeout=3600):
        return cache.set('current_issue', self, timeout)
    
    def __unicode__(self):
        return self.issue_date.strftime('%c')


class ImageSpec():
    """
    Deals with handling files and urls for images of specific size constraints
    Automatigically resizes images to correct constraints
    
    @size => width, height tuple
    @crop_xy => x,y tuple; represents upper left corner of crop region
    
    cached image resizes are saved as 
        (originalName)_(width)x(height).(ext)
    """
    def __init__(self, orig_file, size, crop_xy=None):
        width, height = size
        width = int(min(orig_file.width, width)) if width else None
        height = int(min(orig_file.height, height)) if height else None
        self.width = width or orig_file.width
        self.height = height or orig_file.height
        
        self.orig_file = orig_file
        if crop_xy:
            x, y = crop_xy
            img = pilImage.open(self.orig_file.path)
            img = img.transform(size, pilImage.EXTENT, 
                (x, y, x + self.width,  y + self.height))
            self._path, self._url = self._get_path(), ''
            img.save(self._path)
        else:
            self._path, self._url = '', ''
    
    def _get_path(self):
        """
        calculates the path, no caching involved
        """
        path, ext = splitext(self.orig_file.path)
        path += "_%dx%d%s" % (self.width, self.height, ext)
        return path
    
    @property
    def path(self):
        """
        returns the path; both the path and the autogenerated file are cached
        """
        if self._path:
            return self._path
        path = self._get_path()
        if not exists(path):
            # if it hasn't been precropped or auto generated
            #  autogenerate it
            img = pilImage.open(self.orig_file.path)
            img.thumbnail((self.width, self.height), pilImage.ANTIALIAS)
            img.save(path)
        self._path = path
        return path
    
    @property
    def url(self):
        """
        returns the url; the value is cached. (necessary?)
        """
        if self._url:
           return self._url
        # its a url, so don't use os.path.join
        url = '%s/%s' % (split(self.orig_file.url)[0], split(self.path)[1])
        self._url = url
        return url
        

def get_save_path(instance, filename):
    ext = splitext(filename)[1]
    filtered_capt = filter_string(SAFE_CHARS, instance.kicker)
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + \
        filtered_capt + ext

class Image(Content):
    """
    An image. Handles attributes about image. Handling of image resizing and
    cropping is done by display() and ImageSpec objects
    
    # TODO: not quite sure how to test Image
    
    """
    
    # standard image size constraints
    SIZE_TINY  = (75, 75)
    SIZE_THUMB = (150, 150)
    SIZE_STAND = (600, 600)
    SIZE_LARGE = (900, 900)
    
    caption = models.CharField(blank=False, max_length=1000)
    kicker = models.CharField(blank=False, max_length=500)
    slug = models.SlugField(blank=False, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    # make sure pic is last: get_save_path needs an instance, and if this
    #  attribute is processed first, all the instance attributes will be blank
    pic = models.ImageField('File', upload_to=get_save_path)
    
    @property
    def orientation(self):
        return 'wide' if self.pic.width > self.pic.height else 'tall'
    
    def __getattr__(self, attr):
        "dispatches calls to standard sizes to display()"
        try:
            size = getattr(self.__class__, 'SIZE_%s' % attr.upper())
            return self.display(*size)
        except:
            return getattr(super(Image, self), attr)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    def __init__(self, *args, **kwargs):
        self._spec_cache = {}
        return super(Image, self).__init__(*args, **kwargs)
    
    def display(self, width, height):
        """
        returns an ImageSpec object
        """
        if self._spec_cache.get((width, height), None):
            return self._spec_cache[(width, height)]
        s = ImageSpec(self.pic, (width, height))
        self._spec_cache[(width, height)] = s
        return s
    
    def crop(self, width, height, x, y):
        """
        crops the image and returns an ImageSpec object
        
        overwrites any previous ImageSpecs
        """
        s = ImageSpec(self.pic, (width, height), (x, y))
        self._spec_cache[(width, height)] = s
        return s
    
    def __unicode__(self):
        return self.kicker
    
    @permalink
    def get_absolute_url(self):
        d = self.created_on
        return ('core_get_image', [d.year, d.month, d.day, self.slug])
    
    def save(self, *args, **kwargs):
        # autopopulate the slug
        if not self.slug:
            self.slug = slugify(self.kicker)
        return super(Image, self).save(*args, **kwargs)


class ImageGallery(Content):
    """
    A collection of Images
    """
    
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    images = models.ManyToManyField(Image)
    cover_image = models.ForeignKey(Image, related_name='cover_images')
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    def __unicode__(self):
        return self.title
    
    @permalink
    def get_absolute_url(self):
        return ('core_imagegallery', [self.cover_image.pk, self.pk])
    


class Map(Content):
    """
    A Google Map Object
    """
    title = models.CharField(blank=False, max_length=50) #for internal use, doesn't appear on page
    # values used by Google Maps API
    zoom_level = models.PositiveSmallIntegerField(default=15)
    center_lat = models.FloatField(default=42.373002)
    center_lng = models.FloatField(default=-71.11905)
    display_mode = models.CharField(default='Map', max_length=50)
    width = models.IntegerField(default='300')
    height = models.IntegerField(default='300')
    # display stuff
    caption = models.CharField(blank=True, max_length=1000)
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    def __unicode__(self):
        return self.title  + ' (' + str(self.center_lat) + ',' + str(self.center_lng) + '): ' + str(self.created_on.month) + '/' + str(self.created_on.day) + '/' + str(self.created_on.year)
    


class Marker(models.Model):
    """
    Markers for a Google Map
    """
    map = models.ForeignKey(Map,related_name='markers')
    lat = models.FloatField(blank=False)
    lng = models.FloatField(blank=False)
    popup_text = models.CharField(blank=True, max_length = 1000) #text that appears when the user clicks the marker
    
    def __unicode__(self):
        return self.map.title  + ' (' + str(self.map.center_lat) + ',' + str(self.map.center_lng) + '): ' + self.map.caption + ' (' + str(self.lat) + ',' + str(self.lng) + ')'
    


class ArticlesManager(models.Manager):
    
    # by default, only get published (undeleted) articles
    def get_query_set(self):
        return super(ArticlesManager, self).get_query_set() \
            .filter(is_published=True)
    
    @property
    def recent(self):
        return self.get_query_set() \
            .exclude(generic__issue__web_publish_date__gt=datetime.now()) \
            .order_by('-generic__issue__issue_date', 'generic__priority')
    
    @property
    def web_only(self):
        return self.get_query_set().filter(web_only=True)
    
    @property
    def deleted(self):
        return super(ArticlesManager, self).get_query_set() \
            .filter(is_published=False)

def to_slug(text):
    text = filter_string(SAFE_CHARS+' ', text)
    return text.replace(' ','-')

class Article(Content):
    """
    Non serial text content
    
    # create some articles
    >>> c = Contributor.objects.create(first_name='Kristina',
    ...     last_name='Moore')
    >>> t = Tag.objects.create(text='tagg')
    >>> i = Issue.get_current()
    >>> s = Section.objects.create(name='movies')
    >>> a1 = Article.objects.create(headline='abc', text='abcdefg',
    ...     issue=i, section=s, proofer=c, sne=c)
    >>> a2 = Article.objects.create(headline='head line', 
    ...     text='omg. lolz.', issue=i, section=s, proofer=c, sne=c)
    
    # teasers
    >>> str(a2.long_teaser)
    'omg. lolz.'
    
    # slugs
    >>> str(a1.slug)
    'abc'
    >>> str(a2.slug)
    'head-line'
    """
    
    BYLINE_TYPE_CHOICES = (
        ('cstaff', 'Crimson Staff Writer'),
    )
    
    headline = models.CharField(blank=False, max_length=70)
    subheadline = models.CharField(blank=True, null=True, max_length=150)
    byline_type = models.CharField(
        blank=True, null=True, max_length=70, choices=BYLINE_TYPE_CHOICES)
    text = models.TextField(blank=False)
    teaser = models.CharField(
        blank=True, max_length=1000,
        help_text='If left blank, this will be the first sentence ' \
                    'of the article text.'
    )
    slug = models.SlugField(blank=True, max_length=70, 
        help_text="""
        The text that will be displayed in the URL of this article.
        Can only contain letters, numbers, and dashes (-).
        """)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    page = models.CharField(blank=True, null=True, max_length=10,
        help_text='Page in the print edition.')
    proofer = models.ForeignKey(
        Contributor, related_name='proofed_article_set', 
        limit_choices_to={'is_active': True})
    sne = models.ForeignKey(
        Contributor, related_name='sned_article_set', 
        limit_choices_to={'is_active': True})
    image_gallery = models.ForeignKey(ImageGallery, null=True, blank=True)
    is_published = models.BooleanField(default=True, null=False, blank=False)
    web_only = models.BooleanField(default=False, null=False, blank=False)
    maps = models.ManyToManyField(Map, blank=True)
    
    rel_content = models.ManyToManyField(ContentGeneric,
        through='ArticleContentRelation', null=True, blank=True)
    
    objects = ArticlesManager()
    
    class Meta:
        permissions = (
            ('article.can_change_after_timeout', 
                'Can change articles at any time',),
        )
        #ordering = ['-priority',]
        #unique_together = ('slug', 'issue',)
        get_latest_by = 'created_on'
    
    @property
    def long_teaser(self):
        return truncatewords(self.text, 50)
    
    @property
    def main_rel_content(self):
        r = self.rel_content.all()[:1]
        r = r[0] if r else None
        return r
    
    def save(self, *args, **kwargs):
        # autopopulate the slug
        if not self.slug:
            self.slug = slugify(self.headline)
        return super(Article, self).save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """don't delete articles, just unpublish them"""
        self.is_published = False
        self.save(*args, **kwargs)
    
    def __unicode__(self):
        return self.headline
    
    @permalink
    def get_absolute_url(self):
        d = self.issue.issue_date
        return ('core_get_article', [d.year, d.month, d.day, self.slug])
    


class ArticleContentRelation(models.Model):
    article = models.ForeignKey(Article)
    related_content = models.ForeignKey(ContentGeneric)
    order = models.IntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ('order',)
    
    """
    class Meta:
        unique_together = (
            ('article', 'related_content',), 
            ('article', 'order',),
    )
    """
    

class CrimsonUser(User):
    huid_hash = models.CharField('Harvard ID',
        blank=True, null=True, max_length=255,
        help_text='8 digit HUID. Warning: Without an HUID, this ' \
                'contributor won\'t be able to log on to the website. <br> ' \
                'This number will be encrypted before it is stored.')
                
    def __unicode__(self):
        return self.huid_hash
        
    def __setattr__(self, name, value):
        # hash the huid before storing it; but actually don't
        #if name == 'huid_hash' and value != None:
        #    value = md5(value).digest()
        return super(Contributor, self).__setattr__(name, value)
        
    def parse_token(self):
        # a b c d
        return false