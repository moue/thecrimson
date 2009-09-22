from hashlib import md5
from random import randint
from os.path import splitext, exists, split, join
from datetime import datetime, time, date, timedelta
from re import compile, match, sub
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
from django.db.models.query import QuerySet
from django.http import Http404
from django.template import RequestContext

from crimsononline.common.caching import funcache, expire_page, expire_stuff
from crimsononline.common.forms import \
    MaxSizeImageField, SuperImageField
from crimsononline.common.storage import OverwriteStorage
from crimsononline.common.utils.strings import \
    make_file_friendly, make_url_friendly
from crimsononline.admin_cust.models import Board


class ContentManager(models.Manager):
    """ 
    Base class for managers of Content derived objects
    
    excludes deleted items
    """

    def get_query_set(self):
        return self.all_objects().filter(pub_status=1)
    
    def all_objects(self):
        return super(ContentManager, self).get_query_set()
    
    def admin_objects(self):
        return self.all_objects().exclude(pub_status=-1)
    
    def draft_objects(self):
        return self.all_objects().filter(pub_status=0)
    
    def deleted_objects(self):
        return self.all_objects().filter(pub_status=-1)
    
    @property
    def recent(self):
        return self.get_query_set().order_by('-issue__issue_date', 'priority')
    
    def prioritized(self, recents=7):
        """Order by (priority / days_old).
        
        Arguments:
            recents => only return stuff from the past _ issues. this should 
                make the query have a reasonable run time.
        """
        # TODO: this sql only? works on sqlite3
        # also, round(x - 0.5) == floor(x)
        qs = self.get_query_set().extra(
            tables=['content_issue'], 
            where=['content_issue.id = content_content.issue_id',
                'content_issue.id in (SELECT id FROM content_issue '
                'ORDER BY issue_date DESC LIMIT %s)'
            ],
            params=[recents],
            select={'decayed_priority':
                "content_content.priority / "
                "(round(julianday('now', 'localtime') - "
                "julianday(content_issue.issue_date) - 0.5) + 1)"}
        )
        return qs.extra(order_by=['-decayed_priority',])
    


class Content(models.Model):
    """Base class for all content.
    
    Has some content rendering functions and property access methods.
    """
    
    PUB_CHOICES = (
        (0, 'Draft'),
        (1, 'Published'),
        (-1, 'Deleted'),
    )
    PRIORITY_CHOICES = (
        (1, '1 | one off articles'),
        (2, '2 |'),
        (4, '3 | a normal article'),
        (5, '4 |'),
        (6, '5 |'),
        (7, '6 | kind of a big deal'),
        (9, '7 | lasts ~2 days'),
        (13, '8 |'),
        (17, '9 | ~ 4 days'),
        (21, '10 | OMG, It\'s Faust!'),
    )
    ROTATE_CHOICES = (
        (0, 'Do not rotate'),
        (1, 'Rotate on section pages only'),
        (2, 'Rotate on front and section pages'),
        (3, 'Rotate on front only')
    )
    
    contributors = models.ManyToManyField('Contributor', null=True, 
        related_name='content')
    tags = models.ManyToManyField('Tag', null=True, related_name='content')
    issue = models.ForeignKey('Issue', null=True, related_name='content')
    slug = models.SlugField(max_length=70, help_text="""
        The text that will be displayed in the URL of this article.
        Can only contain letters, numbers, and dashes (-).
        """
    )
    section = models.ForeignKey('Section', null=True, related_name='content')
    priority = models.IntegerField(default=3, choices=PRIORITY_CHOICES)
    group = models.ForeignKey('ContentGroup', null=True, blank=True, 
        related_name='content')
    rotatable = models.IntegerField(null=False, choices=ROTATE_CHOICES, 
        default=0)
    pub_status = models.IntegerField(null=False, choices=PUB_CHOICES, 
        default=0)
    
    content_type = models.ForeignKey(ContentType, editable=False, null=True)
    
    def save(self, *args, **kwargs):
        expire_stuff()
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(self.__class__)
        retval = super(Content, self).save(*args, **kwargs)
        # expire own page
        expire_page(self.get_absolute_url())
        # we should expire the section pag for the content type if it has one
        expire_page(self.section.get_absolute_url())
        # writer page for the contributor of the content
        for contributor in self.contributors.all():
            expire_page(contributor.get_absolute_url())
        # issue for the content
        expire_page(self.issue.get_absolute_url())
        # contentgroup page? I DON'T EVEN KNOW
        if self.group is not None:
            expire_page(self.group.get_absolute_url())
        # all the tag pages woo
        tags = self.tags.all()
        for tag in tags:
            expire_page(tag.get_absolute_url())
        return retval

    @property
    def child(self):
        """Return the instance of the child class.
        
        If c (an instance of Content) was an article, c.child would be
        equivalent to c.article
        """
        child_name = self.content_type.name.replace(" ", "")
        return getattr(self, child_name)
    
    class Meta:
        unique_together = (
            ('issue', 'slug'),
        )
        permissions = (
            ('content.can_publish', 'Can publish content',),
        )
    
    @permalink
    def get_absolute_url(self):
        i = self.issue.issue_date
        url_data = [self.content_type.name.replace(' ', '-'), i.year, 
            i.month, i.day, self.slug]
        if self.group:
            url_data = [self.group.type.lower(), 
                make_url_friendly(self.group.name)] + url_data
            return ('content_grouped_content', url_data)
        else:
            return ('content_content', url_data)
    
    objects = ContentManager()
    
    def _render(self, method, context={}, request=None):
        """Render to some kind of string (usually HTML), depending on method
        
        Always uses the child class
        
        method -- Specification for the render; it could be something like, 
            'admin' or 'search'
        context -- gets injected into template (optional)
        """
        
        name = self.content_type.name.replace(" ","")
        
        templ = 'models/%s/%s.html' % (name, method)
        # can access self with either the name of the class (ie, 'article')
        #   or 'content'
        context.update({name: self.child, 'content': self.child, 'class': name,
                        'disqus': settings.DISQUS})
        
        # print view
        if method == 'page' and request.GET.get('print',""):
            return mark_safe(render_to_string('models/%s/print.html'%(name), context, context_instance=RequestContext(request)))
        
        if method == 'page':
            self.store_hit()
        
        # flyby content
        if method == 'page' and self.group == ContentGroup.flyby:
            return mark_safe(render_to_string('models/%s/flyby.html'%(name), context, context_instance=RequestContext(request)))
        
        return mark_safe(render_to_string(templ, context, context_instance=RequestContext(request)))
    
    def delete(self):
        self.pub_status = -1
        self.save()
    
    # TODO: refactor / simplify store_hit
    def store_hit(self):
        """Store a pageview for this item using lazy storage.
        
        Don't store every hit, just a random sampling of the hits, and only
        hit the database in batches.
        """
        # (Eventual) minimum amount of time to wait between stores to the database
        MIN_DB_STORE_INTERVAL = 1
        # Base number of hits to wait for before storing to the DB
        BASE_THRESHOLD = 4
        # Amount to increase the threshold by each time
        THRESHOLD_JUMP = 5
        # Amount of time to keep number of hits in cache -- we don't want to 
        # lose hits, so make this long.  Note that hits are actually lost 
        # anyway if the threshold still isn't hit in this interval, but if 
        # that happens, the article is so unpopular that either we don't care
        # at all b/c it won't be ranked or The Crimson has no readership left
        HITS_STORE_TIME = 99999
        # The strings we use as cache keys -- should be unique for a given PK
        #  for a given content type on a given day
        thres_str = str(self.pk) + str(self.content_type) + str(date.today()) + 'thres'
        time_str = str(self.pk) + str(self.content_type) + str(date.today()) + 'time'
        hits_str = str(self.pk) + str(self.content_type) + str(date.today()) + 'hits'
        # we want it only once or else the time the code takes to execute will mess things up
        now = datetime.now()
        # If the value was already in the cache
        if not cache.add(thres_str, BASE_THRESHOLD, MIN_DB_STORE_INTERVAL * 3):
            cur_threshold = cache.get(thres_str)
            last_storetime = cache.get(time_str)
        # Add the time value to the cache, using the base threshold (previous 
        #  add already added threshold to cache)
        else:
            cache.add(time_str, now, MIN_DB_STORE_INTERVAL * 3)
            cur_threshold = BASE_THRESHOLD
            last_storetime = now
        # Get the current number of cached hits or initialize it to 1
        try:
            cached_hits = cache.incr(hits_str)
        except ValueError:
            cached_hits = 1
            cache.add(hits_str, 1, HITS_STORE_TIME)
        
        if cur_threshold <= cached_hits:
            # We hit the threshold
            # First check whether the interval between the last time the 
            # threshold was hit and now is less than the minimum
            interval = now - last_storetime
            if interval and interval.seconds < MIN_DB_STORE_INTERVAL:
                # It was, so increase the interval
                cache.set(thres_str, cur_threshold + THRESHOLD_JUMP, MIN_DB_STORE_INTERVAL * 3)
            try:
                ch = ContentHits.objects.get(content = self, date = date.today())
                ch.hits += cached_hits
                ch.save()
            except ContentHits.DoesNotExist:
                ch = ContentHits(content = self)
                ch.hits = cached_hits
                ch.save()
            # Reset a things
            cache.set(time_str, now, MIN_DB_STORE_INTERVAL * 3)
            cache.delete(hits_str)
    
    @staticmethod
    @funcache(3600)
    def types():
        """Return all ContentType objects with parent Content"""
        return [ContentType.objects.get_for_model(cls) 
                for cls in Content.__subclasses__()]
    
    @classmethod
    def find_by_date(cls, start, end):
        """Return a queryset between the two dates"""
        lookup = cls._meta.get_latest_by
        q = {}
        if start:
            q[lookup + '__gte'] = start.date()
        if end:
            q[lookup + '__lte'] = end.date()
        return cls.objects.filter(**q).order_by('-' + lookup)
    


class ContentHits(models.Model):
    content = models.ForeignKey(Content)
    date = models.DateField(auto_now_add=True)
    hits = models.PositiveIntegerField(default=1)
    
    def save(self, *args, **kwargs):
        return super(ContentHits, self).save(*args, **kwargs)
    

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
      * Feature (say, a series on Iraq or the election)
    """
    TYPE_CHOICES = (
        ('column', 'Column'),
        ('series', 'Series'),
        ('blog', 'Blog'),
    )
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    name = models.CharField(max_length=35)
    subname = models.CharField(max_length=40, blank=True, null=True)
    blurb = models.TextField(blank=True, null=True)
    section = models.ForeignKey('Section', blank=True, null=True)
    image = SuperImageField(upload_to=get_img_path, max_width=620,
        blank=True, null=True, storage=OverwriteStorage())
    active = models.BooleanField(default=True, help_text="ContentGroups that " \
        "could still have content posted to them are active.  Active "\
        "blogs and columnists show up on section pages.")
    
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
        # expire own page
        expire_page(self.get_absolute_url())
        # we should expire the section pag for the content type if it has one
        expire_page(self.section.get_absolute_url())
        return s
    
    @permalink
    def get_absolute_url(self):
        return ('content_contentgroup', [self.type, make_url_friendly(self.name)])
    
    @property
    @classmethod
    def flyby(cls):
        try:
            return cls.objects.get(name='FlyBy', type='blog')
        except:
            return cls.objects.create(name='FlyBy', type='blog')

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
    

def contrib_pic_path(instance, filename):
    ext = splitext(filename)[1]
    name = '%s_%s_%s' % \
        (instance.first_name, instance.middle_name, instance.last_name)
    return 'photos/contrib_pics/' + name + ext
    
    
class Contributor(models.Model):
    """
    Someone who contributes to the Crimson, 
    like a staff writer, a photographer, or a guest writer.
    
    # Create a contributor
    >>> c = Contributor(first_name='Dan', middle_name='C',last_name='Carroll')
    
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
    middle_name = models.CharField(blank=True, null=True, max_length=70)
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
    profile_pic = SuperImageField(blank=True, null=True, max_width=135,
        upload_to=contrib_pic_path, storage=OverwriteStorage())
    
    @property
    def profile(self):
        return self.profile_text or self.profile_pic or self.class_of or self.concentration
    
    def __unicode__(self):
        if self.middle_name is None or self.middle_name == '':
            m = ''
        else:
            m = ' ' + self.middle_name
        return '%s%s %s' % (self.first_name, m, self.last_name)
        
    def __setattr__(self, name, value):
        # hash the huid before storing it; but actually don't
        #if name == 'huid_hash' and value != None:
        #    value = md5(value).digest()
        return super(Contributor, self).__setattr__(name, value)
    
    @permalink
    def get_absolute_url(self):
        return ('content_writer_profile', 
            [str(self.id), self.first_name, self.middle_name, self.last_name])


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
        
    def get_absolute_url(self):
        return ('content_section', [make_url_friendly(self.name)])
    
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
        help_text="Leave this blank for daily issues!!!", max_length=100
    )
    web_publish_date = models.DateTimeField(null=True,
        blank=False, help_text='When this issue goes live (on the web).'
    )
    issue_date = models.DateField(
        blank=False, help_text='Corresponds with date of print edition.'
    )
    fm_name = models.CharField('FM name', blank=True, null=True, max_length=100,
        help_text="The name of the FM issue published on this issue date"
    )
    arts_name = models.CharField(blank=True, null=True, max_length=100,
        help_text="The name of the Arts issue published on this issue date"
    )
    comments = models.TextField(
        blank=True, null=True, help_text='Notes about this issue.'
    )
    
    objects = IssueManager()
    
    class Meta:
        ordering = ['-issue_date',]
    
    @property
    def fm_cover(self):
        if not self.fm_name:
            return None
        s = Section.cached('fm')
        a = Article.objects.recent.filter(issue=self,
            rel_content__content_type=Image.content_type(), section=s) \
            .distinct()[:1]
        if a: return a[0].main_rel_content
        else: return None
    
    @property
    def arts_cover(self):
        if not self.arts_name:
            return None
        s = Section.cached('arts')
        a = Article.objects.recent.filter(issue=self,
            rel_content__content_type=Image.content_type(), section=s) \
            .distinct()[:1]
        if a: return a[0].main_rel_content
        else: return None
    
    def get_absolute_url(self):
        return ('content_index', [self.issue_date.year, self.issue_date.month, self.issue_date.day])
    
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
        return self.issue_date.strftime('%A, %B %d, %Y')


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


class ImageManager(ContentManager):

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
    


class Gallery(Content):
    """
    A collection of displayed content (images, youtube, infographics, etc.)
    """
    
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    contents = models.ManyToManyField(Content, through='GalleryMembership',related_name="contents_set")
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']
    
    objects = ContentManager()

    @property
    def cover_image(self):
        if not self.contents:
            return None
        return self.contents.all()[0].child
    
    def __unicode__(self):
        return self.title


class GalleryMembership(models.Model):
    gallery = models.ForeignKey(Gallery, related_name="gallery_set")
    content = models.ForeignKey(Content, related_name="content_set")
    order = models.IntegerField()
    
    class Meta:
        ordering = ('order',)

class YouTubeVideo(Content):
    """
    Embeddable YouTube video
    """
    
    key = models.CharField(blank=False, null=False, max_length=100, 
        help_text="http://www.youtube.com/v=(XXXXXX)&... part of the YouTube URL")
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']

    objects = ContentManager()

    def __unicode__(self):
        return self.title

def get_flash_save_path(instance, filename):
    ext = splitext(filename)[1]
    filtered_title = make_file_friendly(instance.title)
    return datetime.now().strftime("graphics/%Y/%m/%d/%H%M%S_") + \
        filtered_title + ext

class FlashGraphic(Content):
    """
    A Flash Graphic
    """
    
    graphic = models.FileField(upload_to=get_flash_save_path)

    width = models.PositiveIntegerField(help_text="Positive integer less than 640")
    height = models.PositiveIntegerField(help_text="Positive integer")

    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'created_on'
        ordering = ['-created_on']

    def __unicode__(self):
        return self.title
        
    objects = ContentManager()

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
        return self.title    

    objects = ContentManager()

class Marker(models.Model):
    """
    Markers for a Google Map
    """
    map = models.ForeignKey(Map,related_name='markers')
    lat = models.FloatField(blank=False)
    lng = models.FloatField(blank=False)
    popup_text = models.CharField(blank=True, max_length = 1000,
        help_text="text that appears when the user clicks the marker")
    
    def __unicode__(self):
        return str(self.map) + ' (' + str(self.lat) + ',' + str(self.lng) + ')'
    

    

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
    
    """
        
    BYLINE_TYPE_CHOICES = (
        ('cstaff', 'Crimson Staff Writer'),
    )
    
    objects = ContentManager()    
    
    headline = models.CharField(blank=False, max_length=70)
    subheadline = models.CharField(blank=True, null=True, max_length=150)
    byline_type = models.CharField(
        blank=True, null=True, max_length=70, choices=BYLINE_TYPE_CHOICES)
    text = models.TextField(blank=False, null = False)
    teaser = models.CharField(
        blank=True, max_length=1000,
        help_text='If left blank, this will be the first sentence ' \
                    'of the article text.'
    )
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField()
    page = models.CharField(blank=True, null=True, max_length=10,
        help_text='Page in the print edition.')
    proofer = models.ForeignKey(
        Contributor, related_name='proofed_article_set',
        limit_choices_to={'is_active': True})
    sne = models.ForeignKey(
        Contributor, related_name='sned_article_set',
        limit_choices_to={'is_active': True})
    web_only = models.BooleanField(default=False, null=False, blank=False)
    
    rel_content = models.ManyToManyField(Content, through='ArticleContentRelation', 
        null=True, blank=True, related_name = "rel_content")
    
    
    class Meta:
        permissions = (
            ('article.can_change_after_timeout', 
                'Can change articles at any time',),
            )
        get_latest_by = 'created_on'

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_on = datetime.today()
            self.modified_on = datetime.today()
        super(Article, self).save(*args, **kwargs)
    
    @property
    def long_teaser(self):
        return sub(r'<[^>]*?>', '', truncatewords(self.title,50)) 
    
    @property
    def main_rel_content(self):
        r = self.rel_content.all()[:1]
        r = r[0].child if r else None
        # need to return child, so that subclass methods can be called
        return r
    
    def __unicode__(self):
        return self.headline
    
    def identifier(self):
        return self.headline

class ArticleContentRelation(models.Model):
    article = models.ForeignKey(Article, related_name = "ar")
    related_content = models.ForeignKey(Content)
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
    

class Review(models.Model):
    TYPE_CHOICES = (
        ('movie', 'Movie'),
        ('music', 'Music'),
        ('book', 'Book'),
    )
    RATINGS_CHOIES = tuple([(i, str(i)) for i in range(1,6)])
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=RATINGS_CHOIES)
    article = models.ForeignKey(Article, null=True, blank=True)
    created_on = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ('-created_on',)


class Score(models.Model):
    team1 = models.CharField(max_length=50, null=True, blank=True)
    team2 = models.CharField(max_length=50, null=True, blank=True)
    score1 = models.CharField(max_length=20, null=True, blank=True)
    score2 = models.CharField(max_length=20, null=True, blank=True)
    comment = models.CharField(max_length=50, null=True, blank=True)
    event_date = models.DateField()

