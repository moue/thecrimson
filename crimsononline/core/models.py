from hashlib import md5
from random import randint
from os.path import splitext, exists, split
from datetime import datetime
from re import compile, match
from PIL import Image as pilImage
from django.conf import settings
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User, Group

SAFE_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
def get_save_path(instance, filename):
    ext = splitext(filename)[1]
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + \
        ''.join([c for c in instance.caption if c in SAFE_CHARS]) + ext

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
    """
    user = models.ForeignKey(
        User, 
        verbose_name='web user',
        unique=True, 
        blank=True, 
        null=True,
        limit_choices_to={'is_active': True},
        help_text="""
        Only specify a web user if you want this contributor to have web access.<br/>
        To create a new web user, click the green plus sign.<br/>
        To link this contributor to an existing web user, select from the drop-down list.
        """
    )
    first_name = models.CharField(blank=False, null=True, max_length=70)
    last_name = models.CharField(blank=False, null=True, max_length=100)
    middle_initial = models.CharField(blank=True, null=True, max_length=1)
    created_on = models.DateField(auto_now_add=True)
    type = models.CharField(blank=True, null=True, max_length=100)
    profile_text = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.PhoneNumberField(blank=True, null=True)
    board_number = models.IntegerField(
        blank=True, 
        null=True, 
        help_text='Eg: 136'
    )
    boards = models.ManyToManyField(Board, blank=True, null=True)
    class_of = models.IntegerField(blank=True, null=True)
    huid_hash = models.CharField(
        blank=True, 
        null=True, 
        max_length=255,
        help_text='8 digit HUID. This will be encrypted before it is stored.'
    )
    is_active = models.BooleanField(default=True)
    
    def __unicode__(self):
        if self.middle_initial == None or self.middle_initial == '':
            m = ''
        else:
            m = ' ' + self.middle_initial
        return '%s%s %s' % (self.first_name, m, self.last_name)
        
    def __setattr__(self, name, value):
        # hash the huid before storing it
        if name == 'huid_hash' and value != None:
            value = md5(value).digest()
        return super(Contributor, self).__setattr__(name, value)
    
    @permalink
    def get_absolute_url(self):
        return ('core_writer_profile', [str(self.id)])


class Section(models.Model):
    """Eg: News, Sports, etc."""
    
    name = models.CharField(blank=False, max_length=50)
    audiodizer_id = models.IntegerField(blank=True, null=True)
    
    class Admin:
        pass
        
    def __unicode__(self):
        return self.name


class Issue(models.Model):
    """A set of content (articles, photos) for a particular date"""
    
    web_only = models.BooleanField(
        default=False,
        help_text='Check if this issue has no corresponding print edition.'
    )
    web_publish_date = models.DateTimeField(
        blank=False,
        help_text='When this issue goes live (on the web).'
    )
    issue_date = models.DateField(
        blank=False,  
        help_text='Corresponds with date of print edition.'
    )
    comments = models.TextField(
        blank=True, 
        null=True,
        help_text='Notes about this issue.'
    )
    
    def __unicode__(self):
        return self.issue_date.strftime('%c')
    
class Tag(models.Model):
    """A word or phrase used to classify or describe some content"""
    
    text = models.CharField(blank=False, max_length=25, unique=True)
    is_nav = models.BooleanField(default=False)

    def __unicode__(self):
        return self.text


class Image(models.Model):
    """An image"""
    
    pic = models.ImageField('File', upload_to=get_save_path)
    caption = models.CharField(blank=False, max_length=1000)
    kicker = models.CharField(blank=False, max_length=500)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    contributor = models.ForeignKey(
        Contributor,
        limit_choices_to={'is_active': True}
    )
    tags = models.ManyToManyField(Tag)
        
    def get_pic_sized_url(self, width=None, height=None):
        """
        Creates pic smaller than width x height (if pic doesn't exist yet) 
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
        Creates pic smaller than width x height (if pic doesn't exist yet) 
        and returns the filename of the image.
        """
        orig_path = self.pic.path
        if width is None and height is None:
            return orig_path
        elif width is None:
            size = int(height), int(height)
        elif height is None:
            size = int(width), int(width)
        else:
            size = int(width), int(height)
        path, ext = splitext(orig_path)
        path = path + '%dx%d_' % size + ext
        
        #TODO: take into account modify time
        # if the pic doesn't exist, create a new one
        if not exists(path):
            img = pilImage.open(orig_path)
            img.thumbnail(size, pilImage.ANTIALIAS)
            img.save(path)
        return path
    
    def __unicode__(self):
        return self.caption

class ImageGallery(models.Model):
    """A collection of Images"""
    
    images = models.ManyToManyField(Image)
    cover_image = models.ForeignKey(Image, related_name='cover_images')
    created_on = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag)

    def __unicode__(self):
        #return self.cover_image.caption
        return "Image Gallery"

class PublishedArticlesManager(models.Manager):
    """Articles Manager that only returns published articles"""
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set().filter(is_published=True)


class Article(models.Model):
    """Non serial text content"""
    
    BYLINE_TYPE_CHOICES = (
        ('cstaff', 'Crimson Staff Writer'),
    )
    
    headline = models.CharField(
        blank=False, 
        max_length=70, 
        unique_for_date='uploaded_on'
    )    
    subheadline = models.CharField(blank=True, null=True, max_length=70)
    byline_type = models.CharField(
        blank=True,
        null=True,
        max_length=70, 
        choices=BYLINE_TYPE_CHOICES
    )
    text = models.TextField(blank=False)
    teaser = models.CharField(
        blank=True, 
        max_length=1000,
        help_text='If left blank, this will be the first sentence of the article text.'
    )
    contributors = models.ManyToManyField(Contributor)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(
        default=0,
        help_text='Higher priority articles show up at the top of the home page.'
    )
    page = models.CharField(blank=True, null=True, max_length=10)
    proofer = models.ForeignKey(
        Contributor, 
        related_name='proofed_article_set'
    )
    sne = models.ForeignKey(Contributor, related_name='sned_article_set')
    issue = models.ForeignKey(Issue)
    section = models.ForeignKey(Section)
    tags = models.ManyToManyField(Tag)
    image_gallery = models.ForeignKey(ImageGallery, null=True, blank=True)
    is_published = models.BooleanField(default=True, null=False, blank=False)
    
    objects = PublishedArticlesManager()
    all_objects = models.Manager()
    
    class Meta:
        permissions = (
            ('article.can_change_after_timeout', 'Can change articles at any time',),
        )
    
    def delete(self):
        self.is_published = False
        self.save()
    
    def save(self):
        """if theres no teaser, set teaser to the first sentence of text"""
        if self.teaser == None or self.teaser == '':
            self.teaser = self.text.split('.')[0] + '.'
        super(Article, self).save()
    
    def __unicode__(self):
        return self.headline
        
    @permalink
    def get_absolute_url(self):
        return ('core_get_single_article', [str(self.id)])
