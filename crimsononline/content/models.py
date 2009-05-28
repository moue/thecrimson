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
from django.forms import ModelForm
from crimsononline.common.fields import \
    MaxSizeImageField, SuperImageField
from crimsononline.common.storage import OverwriteStorage
from crimsononline.common.utils.strings import \
    make_file_friendly, make_slug, make_url_friendly


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
    Class that contains generic properties.
    
    Facilitates generic relationships between content.
    Only add attributes on which you would want to do cross content queries.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    contributors = models.ManyToManyField(
        'Contributor', null=True, related_name='content')
    tags = models.ManyToManyField('Tag', null=True, related_name='content')
    issue = models.ForeignKey('Issue', null=True, related_name='content')
    section = models.ForeignKey('Section', null=True, related_name='content')
    priority = models.IntegerField(default=0)
    group = models.ForeignKey('ContentGroup', null=True, blank=True)
    hits = models.IntegerField(default=0)
    
    objects = ContentGenericManager()
    
    class Meta:
        unique_together = (('content_type', 'object_id',),)
    
    def __unicode__(self):
        return str(self.content_object)
    


class Content(models.Model):
    """
    Base class for all content.
    
    Has some content rendering functions and generic property access methods.
    """
    
    class Meta:
        abstract = True
    
    def _get_group(self):
        return self.generic.group
    def _set_group(self, value):
        self.generic.group = value
    group = property(_get_group, _set_group)
    
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
    
    def _get_hits(self):
        return self.generic.hits
    def _set_hits(self, value):
        self.generic.hits = value
    hits = property(_get_hits, _set_hits)
    
    generic = models.ForeignKey(ContentGeneric, null=True,
        related_name="%(class)s_generic_related")
    
    def _render(self, method, context={}):
        """
        renders in different ways, depending on method
        
        @method : could be something like, 'admin' or 'search'
        @context : gets injected into template
        """
        name = self._meta.object_name.lower()
        templ = 'models/%s/%s.html' % (name, method)
        # can access self with either the name of the class (ie, 'article')
        #   or 'content'
        context.update({name: self, 'content': self, 'class': name})
        if method == 'page':
            self.hits += 1
            self.save()
        return mark_safe(render_to_string(templ, context))
    
    @staticmethod
    def types():
        # returns all ContentType objects whose 
        #    contenttype has parent class Content
        # TODO: needs MAD caching
        cts = ContentType.objects.filter(app_label='content')
        # HACK: i'm not sure how to grab the parent class (super doesn't work)
        return [ct for ct in cts if hasattr(ct.model_class(), 'generic')]
    
    @classmethod
    def content_type(cls):
        return ContentType.objects.get_for_model(cls)
    
    @classmethod
    def find_by_date(cls, start, end):
        """
        returns a queryset
        """
        lookup = cls._meta.get_latest_by
        q = {}
        if start:
            q[lookup + '__gte'] = start.date()
        if end:
            q[lookup + '__lte'] = end.date()
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
    
    def identifier(self):
        """
        Used in last part of URL.  Child classes should override this.
        This would be like a headline or a title.
        """
        return str(self.pk)
    
    @permalink
    def get_absolute_url(self):
        i = self.issue.issue_date
        url_data = [self.__class__.__name__.lower(), i.year, 
            i.month, i.day, make_url_friendly(self.identifier()), self.pk]
        if self.group:
            url_data = [self.group.type.lower(), 
                make_url_friendly(self.group.name)] + url_data
            return ('content_grouped_content', url_data)
        else:
            return ('content_content', url_data)
    

def get_img_path(instance, filename):
    ext = splitext(filename)[1]
    safe_name = make_file_friendly(instance.name)
    return "images/%s/%s%s" % (instance.type, safe_name, ext)


class ContentGroup(models.Model):
    """
    Groupings of content.  Best for groupings that have simple metadata
        (just a blurb and an image), arbitrary (or chronological) ordering, 
        and not much else.
    This is different from tags because groupings have metadata.
    
    Examples:
      * Columns
      * Blogs
      * Article Series (say, a series on Iraq or the election)
    """
    TYPE_CHOICES = (
        ('column', 'Column'),
        ('series', 'Series'),
        ('blog', 'Blog'),
    )
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    name = models.CharField(max_length=25)
    subname = models.CharField(max_length=40, blank=True, null=True)
    blurb = models.TextField(blank=True, null=True)
    image = SuperImageField(upload_to=get_img_path, max_width=620,
        blank=True, null=True, storage=OverwriteStorage())
    
    class Meta:
        unique_together = (('type', 'name',),)
    
    def __unicode__(self):
        return "%s/%s" % (self.type, self.name)
    
    @staticmethod
    def by_name(type, name):
        """
        Find CGs by type, name key.
        Content Groups shouldn't change that much. We cache them.
        """
        cg = cache.get('contentgroups_all')
        if not cg:
            cg = ContentGroup.update_cache()
        return cg.get((type, name), None)
    
    @staticmethod
    def update_cache():
        """
        This is a separate method, since we want to be add update
        the cache if we create a new content group
        """
        cg = {}
        objs = ContentGroup.objects.all()[:]
        for obj in objs:
            cg[(obj.type, make_url_friendly(obj.name))] = obj
        cache.set('contentgroups_all', cg, 1000000)
        return cg
    
    def save(self, *args, **kwargs):
        """
        When Content Groups change, we need to update the cache
        """
        s = super(ContentGroup, self).save(*args, **kwargs)
        
        return s
    
    @permalink
    def get_absolute_url(self):
        return ('content_contentgroup', [self.type, self.name])


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
    
    # validates in the admin
    text = models.CharField(blank=False, max_length=25, unique=True,
        help_text='Tags can contain letters and spaces')
    
    def __unicode__(self):
        return self.text
    
    @permalink
    def get_absolute_url(self):
        return ('content_tag', [self.text])
    

# TODO: move this out of the content app
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
    
    user = models.OneToOneField(
        User, verbose_name='web user', unique=True, blank=False, 
        null=True,
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
    profile_text = models.TextField(blank=True, null=True,
        help_text="""<b>Text enclosed in [square brackets] 
        will be bold and red</b>""")
    profile_pic = MaxSizeImageField(blank=True, null=True, max_width=150,
        upload_to=contrib_pic_path, storage=OverwriteStorage())
    
    @property
    def profile(self):
        return self.profile_text or self.profile_pic
    
    def __unicode__(self):
        if self.middle_initial is None or self.middle_initial == '':
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
        return ('content_writer_profile', 
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
            a = Section.objects.all()
            cache.set('sections_all', a, 1000000)
        return a
    
    @staticmethod
    def cached(section_name=None):
        a = cache.get('sections_cached')
        if a is None:
            a = dict([(s.name.lower(), s) for s in Section.all()])
            cache.set('sections_cached', a, 1000000)
        if section_name:
            return a[section_name]
        return a
    
    def __unicode__(self):
        return self.name


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
    
    @size_spec => width, height, crop_ratio tuple
    @crop_coords => x1,y1, x2, y2 tuple; represents upper left corner and lower
        right corner of crop region
    
    cached image resizes are saved as 
        (originalName)_(width)x(height).(ext)
    """
    def __init__(self, orig_file, size_spec, crop_coords=None):
        width, height, crop_ratio = size_spec
        # make sure we don't scale images up
        width = int(min(orig_file.width, width)) if width else None
        height = int(min(orig_file.height, height)) if height else None
        self.width = width or orig_file.width
        self.height = height or orig_file.height
        self.crop_ratio = crop_ratio
        self.orig_file = orig_file
        
        if crop_coords:
            img = pilImage.open(self.orig_file.path)
            img = img.transform(size_spec[:2], pilImage.EXTENT, crop_coords)
            self._path = self._get_path()
            img.save(self._path)
        else:
            self._path = ''
        self._url = ''
    
    def _get_path(self):
        """
        calculates the path, no caching involved
        """
        path, ext = splitext(self.orig_file.path)
        c = ("_%f" % self.crop_ratio).replace('.', ',') if self.crop_ratio \
            else ''
        path += "_%dx%d%s%s" % (self.width, self.height, c, ext)
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
            
            # cropped image
            if self.crop_ratio:
                o = self.orig_file
                # autogenerate crop_coordinates
                aspect_ratio = float(o.width) / float(o.height)
                # extra space on left / right => preserve height
                if  aspect_ratio > self.crop_ratio:
                    w = int(o.height * self.crop_ratio)
                    crop_x1 = (o.width - w) / 2
                    crop_coords = (crop_x1, 0, crop_x1 + w, o.height)
                # extra space on top / bottom => preserve width
                elif aspect_ratio < self.crop_ratio:
                    h = int(o.width / self.crop_ratio)
                    crop_y1 = (o.height - h) / 2
                    crop_coords = (0, crop_y1, o.width, crop_y1 + h)
                else:
                    crop_coords = (0, 0, o.width, o.height)
                img = img.transform((self.width, self.height), 
                    pilImage.EXTENT, crop_coords)
            # constrained image
            else:
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
    filtered_capt = make_file_friendly(instance.kicker)
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + \
        filtered_capt + ext

class ImageManager(models.Manager):
    use_for_related_fields = True  
    def get_query_set(self):
        s =  super(ImageManager, self).get_query_set()
        # this is a hella ghetto way to make sure image galleries always return
        # images in the right order.  this is probably really inefficient
        if self.__class__.__name__ == 'ManyRelatedManager':
            s = s.order_by('gallerymembership__order')
        return s
    

class Image(Content):
    """
    An image. Handles attributes about image. Handling of image resizing and
    cropping is done by display() and ImageSpec objects
    
    # TODO: not quite sure how to test Image
    
    """
    
    # standard image size constraints: 
    #  width, height, crop_ratio ( 0 => not cropped )
    SIZE_TINY = (75, 75, 1, 1)
    SIZE_SMALL = (100, 100, 1, 1)
    SIZE_THUMB = (150, 150, 1, 1)
    SIZE_STAND = (600, 600, 0, 0)
    SIZE_LARGE = (900, 900, 0, 0)
    
    caption = models.CharField(blank=True, null=True, max_length=1000)
    kicker = models.CharField(blank=True, null=True, max_length=500)
    slug = models.SlugField(blank=False, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    # make sure pic is last: get_save_path needs an instance, and if this
    #  attribute is processed first, all the instance attributes will be blank
    pic = SuperImageField('File', max_width=960, upload_to=get_save_path)
    
    objects = ImageManager()
    
    @property
    def orientation(self):
        ratio = float(self.pic.width) / float(self.pic.height)
        if ratio >= 1.4:
            return 'wide'
        else:
            return 'tall'
    
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
    
    def display_url(self, size_spec):
        """ convenience method for the pic attribute's method of same name """
        return self.pic.display_url(size_spec)
    
    def crop_thumb(self, size_spec, crop_coords):
        """ convenience method for the pic attribute's method of same name """
        self.pic.crop_thumb(size_spec, crop_coords)
    
    def __unicode__(self):
        return self.kicker
    
    def identifier(self):
        return make_url_friendly(self.kicker)
    
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
    images = models.ManyToManyField(Image, through='GalleryMembership')
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    @property
    def cover_image(self):
        if not self.images:
            return None
        return self.images.all()[0]
    
    def __unicode__(self):
        return self.title
    
    @permalink
    def get_absolute_url(self):
        return ('content_imagegallery', [self.cover_image.pk, self.pk])


class GalleryMembership(models.Model):
    image_gallery = models.ForeignKey(ImageGallery)
    image = models.ForeignKey(Image)
    order = models.IntegerField()
    
    class Meta:
        ordering = ('order',)


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
        """
    )
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
        r = r[0].content_object if r else None
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
    
    def identifier(self):
        return self.headline
    


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
    

class UserData(models.Model):
    user = models.ForeignKey(User, unique=True)
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
        return super(UserData, self).__setattr__(name, value)
        
    def parse_token(self):
        # a b c d
        return False

class Subscription(models.Model):
	email = models.EmailField(blank=False)
	contributors = models.ManyToManyField(Contributor,blank=True)
	section = models.ManyToManyField(Section,blank=True)
	tags = models.ManyToManyField(Tag,blank=True)
	def __unicode__(self):
		return self.email

class SubscriptionForm(ModelForm):
	class Meta:
		model = Subscription