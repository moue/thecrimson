from hashlib import md5
from random import randint
from os.path import splitext, exists, split
from datetime import datetime, time
from re import compile, match
from string import letters, digits
from PIL import Image as pilImage
from django.conf import settings
from django.db import models
from django.db.models import permalink, Q
from django.contrib.auth.models import User, Group
from django.contrib.localflavor.us.models import PhoneNumberField
from django.core.cache import cache
from django.template.defaultfilters import slugify, truncatewords

SAFE_CHARS = letters + digits
def filter_string(allowed_chars, str):
    return ''.join([c for c in str if c in allowed_chars])


class Tag(models.Model):
    """
    A word or phrase used to classify or describe some content.
    
    # A bit of setup
    >>> from django.db import IntegrityError:
    
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
    
    # url
    >>> tag1.get_absolute_url()
    '/tag/potato/'
    
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
    """
    name = models.CharField(blank=False, null=False, max_length=20)
    group = models.ForeignKey(Group, null=True, blank=True)
    
    def __unicode__(self):
        return self.name


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
    
    # Check the hashing of HUIDs
    >>> c.huid_hash='12345678'
    '%\xd5Z\xd2\x83\xaa@\n\xf4d\xc7mq<\x07\xad'
    
    #Still need to test permalinks...
    """
    user = models.ForeignKey(
        User, verbose_name='web user', unique=True, blank=True, 
        null=True, limit_choices_to={'is_active': True},
    )
    first_name = models.CharField(blank=False, null=True, max_length=70)
    last_name = models.CharField(blank=False, null=True, max_length=100)
    middle_initial = models.CharField(blank=True, null=True, max_length=1)
    created_on = models.DateField(auto_now_add=True)
    type = models.CharField(blank=True, null=True, max_length=100)
    profile_text = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)
    board_number = models.IntegerField(
        blank=True, null=True, help_text='Eg: 136')
    boards = models.ManyToManyField(Board, blank=True, null=True)
    class_of = models.IntegerField(blank=True, null=True)
    huid_hash = models.CharField('Harvard ID',
        blank=True, null=True, max_length=255,
        help_text='8 digit HUID. Warning: Without an HUID, this ' \
                'contributor won\'t be able to log on to the website. <br> ' \
                'This number will be encrypted before it is stored.')
    is_active = models.BooleanField(default=True,
        help_text='This should be true for anyone who could possibly still ' \
                    'write for The Crimson, including guest writers.')
    
    def __unicode__(self):
        if self.middle_initial == None or self.middle_initial == '':
            m = ''
        else:
            m = ' ' + self.middle_initial + '.'
        return '%s%s %s' % (self.first_name, m, self.last_name)
        
    def __setattr__(self, name, value):
        # hash the huid before storing it
        #if name == 'huid_hash' and value != None:
        #    value = md5(value).digest()
        return super(Contributor, self).__setattr__(name, value)
    
    @permalink
    def get_absolute_url(self):
        return ('core_writer_profile', 
            [str(self.id), self.first_name, self.middle_initial, self.last_name])


class Section(models.Model):
    """Eg: News, Sports, etc."""
    
    name = models.CharField(blank=False, max_length=50)
    audiodizer_id = models.IntegerField(blank=True, null=True)
    
    @staticmethod
    def all():
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
            .filter(Q)

class SpecialIssueManager(LiveIssueManager):
    """Only returns named issues"""    
    def get_query_set(self):
        return super(SpecialIssueManager, self).get_query_set() \
            .exclude(Q(special_issue_name="") | Q(special_issue_name=None))

class DailyIssueManager(LiveIssueManager):
    """Only returns unnamed issues"""
    def get_query_set(self):
        return super(DailyIssueManager, self).get_query_set() \
            .filter(Q(special_issue_name="") | Q(special_issue_name=None))

class Issue(models.Model):
    """
    A set of content (articles, photos) for a particular date.
    
    Special issues should NEVER be displayed by default on the index.
    They should be displayed via content modules or special redirects.
    """
    
    special_issue_name = models.CharField(blank=True, null=True,
        help_text="Leave this blank for daily issues!!!", max_length=100)
    web_publish_date = models.DateTimeField(null=True,
        blank=False, help_text='When this issue goes live (on the web).')
    issue_date = models.DateField(
        blank=False, help_text='Corresponds with date of print edition.')
    comments = models.TextField(
        blank=True, null=True, help_text='Notes about this issue.')
    
    objects = models.Manager()
    special_objects = SpecialIssueManager()
    daily_objects = DailyIssueManager()
    live_objects = LiveIssueManager(live=True)
    live_special_objects = SpecialIssueManager(live=True)
    live_daily_objects = DailyIssueManager(live=True)
    
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


def get_save_path(instance, filename):
    ext = splitext(filename)[1]
    filtered_capt = filter_string(SAFE_CHARS, instance.kicker)
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + \
        filtered_capt + ext

class Image(models.Model):
    """An image"""
    
    caption = models.CharField(blank=False, max_length=1000)
    kicker = models.CharField(blank=False, max_length=500)
    created_on = models.DateTimeField(auto_now_add=True)
    contributor = models.ForeignKey(
        Contributor, limit_choices_to={'is_active': True})
    tags = models.ManyToManyField(Tag, blank=False)
    # make sure pic is last: get_save_path needs an instance, and if this
    #  attribute is processed first, all the instance attributes will be blank
    pic = models.ImageField('File', upload_to=get_save_path)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    def get_pic_sized_url(self, width=None, height=None):
        """
        Creates pic smaller than width x height y (if pic doesn't exist yet) 
        and returns the url of the image.
        """
        url = self.pic.url
        if width is None and height is None:
            return url
        url = split(url)[0]
        file = split(self.get_pic_sized_path(width, height))[1]
        return url + '/' + file
    
    def get_pic_sized_path(self, width=None, height=None):
        """
        Creates pic smaller than width x height y (if pic doesn't exist yet) 
        and returns the filename of the image.
        """
        orig_path = self.pic.path
        width = int(min(self.pic.width, width)) if width else None
        height = int(min(self.pic.height, height)) if height else None
        if (width is None and height is None):
            return orig_path
        else:
            size = [width or self.pic.width, height or self.pic.height]
            size = tuple([int(i) for i in size])
        path, ext = splitext(orig_path)
        
        #TODO: take into account modify time #
        # if the pic doesn't exist, create a new one
        if not exists(path):
            img = pilImage.open(orig_path)
            img.thumbnail(size, pilImage.ANTIALIAS)
            path = path + '%dx%d_' % img.size + ext
            img.save(path)
        return path
    
    def __unicode__(self):
        return self.kicker


class ImageGallery(models.Model):
    """A collection of Images"""
    
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    images = models.ManyToManyField(Image)
    cover_image = models.ForeignKey(Image, related_name='cover_images')
    created_on = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=False)
    
    def __unicode__(self):
        return self.title
    
    @permalink
    def get_absolute_url(self):
        return ('core_imagegallery', [self.cover_image.pk, self.pk])


class PublishedArticlesManager(models.Manager):
    """Articles Manager that only returns published articles"""
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set() \
            .filter(is_published=True)

class WebOnlyManager(PublishedArticlesManager):
    """Articles Manager that only returns web only articles"""
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set() \
            .filter(web_only=True)

class RecentsManager(PublishedArticlesManager):
    """Article Manager that returns the most recent articles"""
    def get_query_set(self):
        return super(RecentsManager, self).get_query_set() \
            .exclude(issue__web_publish_date__gt=datetime.now()) \
            .order_by('-issue__issue_date', 'priority')

def to_slug(text):
    text = filter_string(SAFE_CHARS+' ', text)
    return text.replace(' ','-')
    
class Article(models.Model):
    """Non serial text content"""
    
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
    contributors = models.ManyToManyField(
        Contributor, limit_choices_to={'is_active': True},
        help_text='Who wrote this article')
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(default=0, 
        help_text='Higher priority articles are displayed first.' \
        'Priority be positive or negative.')
    page = models.CharField(blank=True, null=True, max_length=10,
        help_text='Page in the print edition.')
    proofer = models.ForeignKey(
        Contributor, related_name='proofed_article_set', 
        limit_choices_to={'is_active': True})
    sne = models.ForeignKey(
        Contributor, related_name='sned_article_set', 
        limit_choices_to={'is_active': True})
    issue = models.ForeignKey(Issue, null=False, blank=False, 
        help_text='If this is a web only article, then Issue is the print' \
                    ' issue this article should be displayed with.')
    section = models.ForeignKey(Section)
    image_gallery = models.ForeignKey(ImageGallery, null=True, blank=True)
    is_published = models.BooleanField(default=True, null=False, blank=False)
    web_only = models.BooleanField(default=False, null=False, blank=False)
    tags = models.ManyToManyField(Tag, blank=False, help_text="""
        Short descriptors for this article.
        Try to use tags that already exist, if  possible.
        """)
    
    objects = PublishedArticlesManager()
    web_objects = WebOnlyManager()
    all_objects = models.Manager()
    recent_objects = RecentsManager()
    
    class Meta:
        permissions = (
            ('article.can_change_after_timeout', 
                'Can change articles at any time',),
        )
        ordering = ['-priority',]
        unique_together = ('slug', 'issue',)
    
    def get_long_teaser(self):
        return truncatewords(self.text, 50)
    long_teaser = property(get_long_teaser)
    
    def save(self):
        # autopopulate the slug
        if not self.slug:
            self.slug = slugify(self.headline)
        return super(Article, self).save()
    
    def delete(self):
        """don't delete articles, just unpublish them"""
        self.is_published = False
        self.save()
    
    def __unicode__(self):
        return self.headline
    
    @permalink
    def get_absolute_url(self):
        d = self.issue.issue_date
        return ('core_get_article', [d.year, d.month, d.day, self.slug])
