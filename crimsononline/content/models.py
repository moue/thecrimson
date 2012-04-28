from hashlib import md5
from random import randint
from os.path import splitext, exists, split, join, basename
import os
from datetime import datetime, time, date, timedelta
from django.utils.datetime_safe import strftime
from re import compile, match, sub
from string import letters, digits
from PIL import Image as pilImage
import copy
import urllib

from django.conf import settings
from django.core import urlresolvers
from django.db import models
from django.db.models import permalink, Q, Count
from django.db.models.fields.files import ImageFieldFile
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.localflavor.us.models import PhoneNumberField
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.template import TemplateDoesNotExist
from django.template.defaultfilters import slugify, truncatewords
from django.template.loader import render_to_string, get_template
from django.utils.safestring import mark_safe
from django.forms import ModelForm
from django.db.models.query import QuerySet
from django.http import Http404
from django.template import RequestContext
from django.utils.datetime_safe import strftime as strftime_safe
from django.utils import simplejson

from crimsononline.admin_cust.models import UserData
from crimsononline.common.caching import funcache, expire_page, expire_stuff
from crimsononline.common.fields import \
    MaxSizeImageField, SuperImageField
from crimsononline.common.storage import OverwriteStorage
from crimsononline.common.utils.misc import ret_on_fail
from crimsononline.common.utils.strings import \
    make_file_friendly, make_url_friendly, rand_str
from crimsononline.admin_cust.models import Board


def add_issue_filter(f):
    """Modify a manager method to add a filter for restricting by issue date.

    Adds the ability to process (optional) start and end dates
    """
    def f_prime(*args, **kwargs):
        start = kwargs.pop('start', None)
        end = kwargs.pop('end', None)
        if start is None and end is None:
            return f(*args, **kwargs)
        q = {}
        if start:
            if isinstance(start, datetime):
                start = start.date()
            q['issue__issue_date__gte'] = start
        if end:
            if isinstance(end, datetime):
                end = end.date()
            q['issue__issue_date__lte'] = end
        return f(*args, **kwargs).filter(**q)
    return f_prime

class ContentManager(models.Manager):
    """Base class for managers of Content derived objects."""

    def rel_content_ordered(self):
        """Ordered for Article.rel_content

        #TODO: this is a HUGE hack, most notably, it probably fucks up
            all other content with many related managers
        """
        return self.all_objects().filter(pub_status=1).order_by(
            'articlecontentrelation__order'
        )

    #TODO: make this date crap into a decorator or something

    @add_issue_filter
    def get_query_set(self):
        # hack to ensure that related content gets ordered
        if self.__class__.__name__ == 'ManyRelatedManager':
            return self.rel_content_ordered()
        return self.all_objects().filter(pub_status=1)
        #return QuerySet(self.model, using=self._db, query=MySQLOptimizedQuery(self.model)).filter(pub_status=1)

    @add_issue_filter
    def all(self):
        return self.get_query_set()

    @add_issue_filter
    def all_objects(self):
        return super(ContentManager, self).get_query_set()

    @add_issue_filter
    def admin_objects(self):
        return self.all_objects().select_related(depth=2).exclude(pub_status=-1)

    @add_issue_filter
    def draft_objects(self):
        return self.all_objects().select_related(depth=2).filter(pub_status=0)

    @add_issue_filter
    def deleted_objects(self):
        return self.all_objects().select_related(depth=2).filter(pub_status=-1)

    @property
    def recent(self):
        return self.get_query_set().order_by('-created_on')

    def prioritized(self, recents=7):
        """Order by (priority / days_old).

        Arguments:
            recents=N => only return stuff from the past N issues. this should
                make the query have a reasonable run time.
        """
        issue_pks = [str(i.pk) for i in Issue.last_n(recents)]
        # round(x - 0.5) == floor(x)
        if settings.DATABASE_ENGINE == 'sqlite3':
            days_old_expr = "(round(julianday('now', 'localtime') - " \
                "julianday(content_issue.issue_date) - 0.5) + 1)"
        elif settings.DATABASE_ENGINE == 'mysql':
            days_old_expr = '(DATEDIFF(NOW(), content_issue.issue_date) + 1)'
        else:
            raise Exception("Database not supported")
        qs = self.get_query_set().extra(
            tables=['content_issue'],
            where=['content_issue.id = content_content.issue_id',
                'content_issue.id in (%s)' % ', '.join(issue_pks)
            ],
            select={'decayed_priority':
                "content_content.priority / " + days_old_expr
            }
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
        (0, 'Don\'t'),
        (1, 'Section Only'),
        (2, 'Front and Section'),
        (3, 'Front Only')
    )

    contributors = models.ManyToManyField('Contributor', null=True,
        related_name='content')
    tags = models.ManyToManyField('Tag', null=True, related_name='content')
    issue = models.ForeignKey('Issue', null=False, related_name='content')
    slug = models.SlugField(max_length=70, help_text="""
        The text that will be displayed in the URL of this article.
        Can only contain letters, numbers, and dashes (-).
        """
    )
    section = models.ForeignKey('Section', null=False, related_name='content')
    priority = models.IntegerField(default=3, choices=PRIORITY_CHOICES,
        db_index=True)
    group = models.ForeignKey('ContentGroup', null=True, blank=True,
        related_name='content')
    rotatable = models.IntegerField(null=False, choices=ROTATE_CHOICES,
        default=0, db_index=True)
    pub_status = models.IntegerField(null=False, choices=PUB_CHOICES,
        default=0, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_on = models.DateTimeField(auto_now=True, db_index=True)
    old_pk = models.IntegerField(null=True, help_text="primary key "
                                 "from the old website.", db_index=True)

    content_type = models.ForeignKey(ContentType, editable=False, null=True)

    def save(self, *args, **kwargs):
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(self.__class__)
        retval = super(Content, self).save(*args, **kwargs)
        try:
            expire_stuff()
            # expire own page
            expire_page(self.get_absolute_url())
            # we should expire the section page for the content type if it has one
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
            for tag in self.tags.all():
                expire_page(tag.get_absolute_url())
        except:
            pass
        return retval

    @classmethod
    def ct(cls):
        """Returns the content type for this class.

        Note that ContentType.objects already caches
        """
        return ContentType.objects.get_for_model(cls)
    
    @property
    def num_comments(self):
        page_url = "%s%s" % (settings.URL_BASE, self.get_absolute_url()[1:])
        # use the top one if it works
        #page_url = "%s%s" % ("http://www.thecrimson.com/", "article/2010/5/14/school-law-kagan-staff/")

        disqus_thread_url = "http://disqus.com/api/get_thread_by_url?forum_api_key=%s&url=%s" % (settings.DISQUS_FORUM_KEY, page_url)

        num_comments = 0
        try:
            num_comments = simplejson.load(urllib.urlopen(disqus_thread_url))["message"]["num_comments"]
        except:
            pass
            
        return num_comments

    @property
    def child(self):
        """Return the instance of the child class.

        If c (an instance of Content) was an article, c.child would be
        equivalent to c.article
        """
        child_name = self.content_type.name.replace(" ", "")
        try:
            return getattr(self, child_name)
        except ObjectDoesNotExist: # db integrity error
            # parent exists, but child doesn't exist.  since the child data
            #  doesn't exist, might as well delete the parent to prevent
            #  further errors
            self.delete()
            raise


    class Meta:
        unique_together = (
            ('issue', 'slug'),
        )
        permissions = (
            ('content.can_publish', 'Can publish content',),
            ('content.can_unpublish', 'Can unpublish content',),
            ('content.can_delete_published', 'Can delete published content'),
        )
        get_latest_by = 'created_on'
        #abstract = True

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

    def get_full_url(self):
        """ includes domain """
        return "%s%s" % (settings.URL_BASE, self.get_absolute_url()[1:])
        
    def get_admin_change_url(self):
        return urlresolvers.reverse('admin:content_%s_change' \
                                    % str(self.content_type).replace(' ', '_'),
                                    args=(self.pk,))

    def __unicode__(self):
        return self.child.__unicode__()

    objects = ContentManager()

    def _render(self, method, context={}, request=None):
        """Render to some kind of string (usually HTML), depending on method

        Always uses the child class

        method -- Specification for the render; it could be something like,
            'admin' or 'search'
        context -- gets injected into template (optional)
        """
        n_context = copy.copy(context)
        nav = self.section.name.lower()
        name = self.content_type.name.replace(" ","")
        ext = '.html' if method[-4:] != '.txt' else ''
        
        if self.content_type == ContentType.objects.get(name="map"):
            n_context.update({'google_api_key': settings.GOOGLE_API_KEY})
        
        # TODO fix this block to not be horrible
        if self.group:
            try:
                templ = ('models/%s/contentgroup/%s/%s/%s%s' %
                    (name, self.group.type, make_url_friendly(self.group.name), method, ext))
                # The call to get_template is to raise TemplateDoesNotExist if,
                # in fact, the template doesn't exist.  Its return value isn't used.
                get_template(templ)
                n_context['url_base'] = "/%s/%s" % (self.group.type, make_url_friendly(self.group.name))
            except TemplateDoesNotExist:
                templ = 'models/%s/%s%s' % (name, method, ext)
        else:
            templ = 'models/%s/%s%s' % (name, method, ext)

        # dumb hack for this jerk
        if self.slug in ['news-in-brief-student-charged-with', 'police-arrest-junior-for-assault-span',
                        'four-undergrads-face-drug-charges-span', 'students-plead-not-guilty-to-drug',
                        'charges-follow-lengthy-watch-divspan-classapple-style-span', 'judge-sets-next-date-in-marijuana',
                        'judge-moves-to-dismiss-dewolfe-drug', 'judge-may-dismiss-dewolfe-drugs-case',
                        'mcginn-n-tonic-revisiting-harvard-football', 'hefs-got-nothin-on-harvards-hottest',
                        'leave-of-absence-harvard', 'police-arrest-student-for-possession-of',
                        'color-line-cuts-through-the-heart', 'scoped-jordan-b-weitzen-08-span','student-arrested-for-quad-break-in-after']:
            noindex = True
        else:
            noindex = False
        # TODO: Allow this to be specified via the admin
        # can access self with either the name of the class (ie, 'article')
        #   or 'content'
        pcrs = PackageSectionContentRelation.objects.filter(related_content=self)
        if len(pcrs) > 0:
            featureStr = pcrs[0].FeaturePackageSection.MainPackage.title
            featureSlug = pcrs[0].FeaturePackageSection.MainPackage.slug
            sectionStr = pcrs[0].FeaturePackageSection.title
            sectionSlug = pcrs[0].FeaturePackageSection.slug
            n_context.update({'feature': featureStr, 'fSection': sectionStr, 'featureSlug':featureSlug, 'sectionSlug':sectionSlug})
            
        n_context.update({name: self.child, 'content': self.child,
                        'class': name, 'disqus': settings.DISQUS, 'nav':nav, 'noindex':noindex})

        if method == 'page':
            # print view
            if request is not None and request.GET.get('print',""):
                return mark_safe(render_to_string('models/%s/print.html'%(name),
                                 n_context))

            self.store_hit()

            # flyby content
            if self.section == Section.cached('flyby') and self.content_type == Article.ct():
                # TODO: This is bad; fix it
                section = self.section
                series = list(ContentGroup.objects.filter(active=True).filter(section=section))
                from crimsononline.content.views import rotatables
                from crimsononline.common.utils.lists import first_or_none
                featured = rotatables(section)
                video = first_or_none(YouTubeVideo.objects.recent.filter(section=section))
                n_context.update({'section': section,
                                  'series': series,
                                  'featured': featured,
                                  'video': video})
                return mark_safe(render_to_string('models/%s/flyby.page.html'%(name),
                                 n_context))

        return mark_safe(render_to_string(templ, n_context))

    def delete(self):
        # anyone can delete drafts
        if int(self.pub_status) is 0:
            super(Content, self).delete()
        else:
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
        thres_str = str(self.pk) + str(self.content_type).replace(" ","") + str(date.today()) + 'thres'
        time_str = str(self.pk) + str(self.content_type).replace(" ","") + str(date.today()) + 'time'
        hits_str = str(self.pk) + str(self.content_type).replace(" ","") + str(date.today()) + 'hits'
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
        if cached_hits is None:
            cached_hits = 1
            cache.add(hits_str, 1, HITS_STORE_TIME)
        if last_storetime is None:
            last_storetime = now
        if cur_threshold <= cached_hits:
            # We hit the threshold
            # First check whether the interval between the last time the
            # threshold was hit and now is less than the minimum
            interval = now - last_storetime
            if interval and interval.seconds < MIN_DB_STORE_INTERVAL:
                # It was, so increase the interval
                cache.set(thres_str, cur_threshold + THRESHOLD_JUMP, MIN_DB_STORE_INTERVAL * 3)
            try:
                ch = ContentHits.objects.filter(content=self, date = date.today())[0]
                ch.hits += cached_hits
            except (ContentHits.DoesNotExist, IndexError):
                ch = ContentHits(content=self)
                ch.hits = cached_hits

            #ch.save()

            # Reset a things
            cache.set(time_str, now, MIN_DB_STORE_INTERVAL * 3)
            cache.delete(hits_str)

    @staticmethod
    @funcache(3600)
    def types():
        """Return all ContentType objects with parent Content"""
        return [ContentType.objects.get_for_model(cls)
                for cls in Content.__subclasses__()]

class ContentHits(models.Model):
    content = models.ForeignKey(Content, db_index=True)
    date = models.DateField(auto_now_add=True, db_index=True)
    hits = models.PositiveIntegerField(default=1)

    def __unicode__(self):
        return "Content %d with %d hits" % (self.content_id, self.hits)


def get_img_path(instance, filename):
    ext = splitext(filename)[1]
    safe_name = make_file_friendly(instance.name)
    return "photos/contentgroups/%s/%s%s" % (instance.type, safe_name, ext)

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

    type = models.CharField(max_length=25, choices=TYPE_CHOICES, db_index=True)
    name = models.CharField(max_length=35, db_index=True)
    subname = models.CharField(max_length=40, blank=True, null=True)
    blurb = models.TextField(blank=True, null=True)
    section = models.ForeignKey('Section', blank=True, null=True)
    image = SuperImageField(upload_to=get_img_path, max_width=300,
        blank=True, null=True, storage=OverwriteStorage(),
        help_text='Thumbnail')
    active = models.BooleanField(default=True, help_text="ContentGroups that " \
        "could still have content posted to them are active.  Active "\
        "blogs and columnists show up on section pages.", db_index=True)

    class Meta:
        unique_together = (('type', 'name',),)
        verbose_name_plural = "Content Groups"

    def __unicode__(self):
        return "%s/%s" % (self.type, self.name)

    def delete(self):
        self.content.clear()
        super(ContentGroup, self).delete()

    @staticmethod
    def by_name(type, name):
        """
        Find CGs by type, name key.
        Content Groups shouldn't change that much. We cache them.
        """
        cg = cache.get('contentgroups_all')
        # If contentgroups_all has expired, get it again
        if not cg:
            cg = ContentGroup.update_cache()
            cg_refreshed = True
        else:
            cg_refreshed = False
        # We expect that most of the calls to by_name will be for groups that
        # actually exist, so if a group isn't found in the cached list, we
        # refresh the cache and look again.
        obj = cg.get((type, name), None)
        if not obj and not cg_refreshed:
            cg = ContentGroup.update_cache()
            obj = cg.get((type, name), None)
        return obj

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
        try:
        # expire own page
            expire_page(self.get_absolute_url())
            # we should expire the section pag for the content type if it has one
            if(self.section):
                expire_page(self.section.get_absolute_url())
            ContentGroup.update_cache()
        except:
            raise
        return s

    @permalink
    def get_absolute_url(self):
        return ('content_contentgroup', [self.type, make_url_friendly(self.name)])


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

    CATEGORY_CHOICES = (
        ('sports', 'Sports'),
        ('college', 'College'),
        ('faculty', 'Faculty'),
        ('university', 'University'),
        ('city', 'City'),
        ('stugroups', 'Student Groups'),
        ('houses', 'Houses'),
        ('depts', 'Departments'),
        ('', 'Uncategorized')
    )

    # validates in the admin
    text = models.CharField(blank=False, max_length=25, unique=True,
        help_text='Tags can contain letters and spaces', db_index=True)
    category = models.CharField(blank=True, max_length=25,
                                choices=CATEGORY_CHOICES, db_index=True)

    def __unicode__(self):
        return self.text

    """
    # This is incredibly slow right now
    @staticmethod
    def top_by_section(section,range=30,n=10):
        # Range is the number of days to look back for tags
        too_old = datetime.now() - timedelta(days = range)
        tags = Tag.objects.all() \
                .filter(content__section=section) \
                .filter(content__issue__issue_date__gt = too_old) \
                .annotate(content_count=Count('content')) \
                .order_by('-content_count')[:n]
        return tags
    """

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

    userdata = models.OneToOneField(
        UserData, verbose_name='web user', unique=True, blank=False,
        null=True, related_name='contributor',
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
    is_active = models.BooleanField(default=True, db_index=True,
        help_text='This should be true for anyone who could possibly still ' \
                    'write for The Crimson, including guest writers.')
    profile_text = models.TextField(blank=True, null=True,
        help_text="""<b>Text enclosed in [square brackets]
        will be bold and red</b>""")
    profile_pic = SuperImageField(blank=True, null=True, max_width=131,
        upload_to=contrib_pic_path, storage=OverwriteStorage())

    class Meta:
        ordering = ('last_name',)

    @property
    def user(self):
        if self.userdata is not None:
            return self.userdata.user
        else:
            return None

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
    get_absolute_url = ret_on_fail(get_absolute_url, '')


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

    name = models.CharField(blank=False, max_length=50, db_index=True)
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

    """
    def top_tags(self,range=30,n=10):
        return Tag.top_by_section(self,range)
    """

    @permalink
    def get_absolute_url(self):
        return ('content.section.%s' % self.name.lower(), [])

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
        help_text="Leave this blank for daily issues!!!", max_length=100,
        db_index=True
    )
    web_publish_date = models.DateTimeField(null=True,
        blank=False, help_text='When this issue goes live (on the web).'
    )
    issue_date = models.DateField(
        blank=False, help_text='Corresponds with date of print edition.',
        db_index=True
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
        return a[0].main_rel_content if a else None

    @property
    def arts_cover(self):
        if not self.arts_name:
            return None
        s = Section.cached('arts')
        a = Article.objects.recent.filter(issue=self,
            rel_content__content_type=Image.content_type(), section=s) \
            .distinct()[:1]
        if a is not None:
            return a[0].main_rel_content
        else:
            return None

    @permalink
    def get_absolute_url(self):
        return ('content_index', [self.issue_date.year, self.issue_date.month, self.issue_date.day])

    #TODO: funcache this
    @staticmethod
    def last_n(n, rece_date=None):
        """Last n issue, by date, only chooses issues >= rece_date"""
        i = cache.get('last_%d_issues_%s' % (n, str(rece_date)))
        if rece_date is None:
            rece_date = date.today()
        if i is None:
            i = Issue.objects.filter(issue_date__lte=rece_date)\
                             .order_by('-issue_date')[:n]
            cache.set('last_%d_issues' % n, i, 60*60)
        if len(i) == 0:
            raise Exception("There are no issues.")
        return i

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
        if self.issue_date.year >= 1900:
            return self.issue_date.strftime('%A, %B %d, %Y')
        return strftime_safe(self.issue_date, '%A, %B %d, %Y')


class ImageManager(ContentManager):
    def get_query_set(self):
        s =  super(ImageManager, self).get_query_set()
        # this is a hella ghetto way to make sure image galleries always return
        # images in the right order.  this is probably really inefficient
        if self.__class__.__name__ == 'ManyRelatedManager':
            s = s.order_by('gallerymembership__order')
        return s


def image_get_save_path(instance, filename):
    ext = splitext(filename)[1]
    key = rand_str(10) if instance.pk is None else str(instance.pk)
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + key + ext

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
    SIZE_STAND = (630, 630, 0, 0)
    SIZE_LARGE = (900, 900, 0, 0)

    caption = models.CharField(blank=True, null=True, max_length=1000)
    kicker = models.CharField(blank=True, null=True, max_length=500)
    # make sure pic is last: photo_save_path needs an instance, and if this
    #  attribute is processed first, all the instance attributes will be blank
    pic = SuperImageField('File', max_width=960, upload_to=image_get_save_path)
    # Data for crops.  We store the 1:1 ratio crop as the location of its top left
    # corner and the length of a side.
    crop_x = models.IntegerField(null=True)
    crop_y = models.IntegerField(null=True)
    crop_side = models.IntegerField(null=True)

    objects = ImageManager()

    @property
    def img_title(self):
        """Title / alt for <img> tags."""
        return self.kicker

    @property
    def orientation(self):
        try:
            ratio = float(self.pic.width) / float(self.pic.height)
        # TODO figure out which exception is raised when self.pic can't be found
        except:
            ratio = 1
        if ratio >= 1.4:
            return 'wide'
        else:
            return 'tall'

    def save(self, *args, **kwargs):
        newpath = kwargs.pop('newpath', False)
        super(Image, self).save(*args, **kwargs)
        a = basename(self.pic.path)
        b = newpath or image_get_save_path(self, self.pic.path)
        # move the image
        if a.split('_')[-1] != basename(b).split('_')[1]:
            new_path = self.pic.path.replace(a, basename(b))
            os.rename(self.pic.path, new_path)
            self.pic.name = b
            super(Image, self).save(*args, **kwargs)


    def __getattr__(self, attr):
        "dispatches calls to standard sizes to display()"
        try:
            size = getattr(self.__class__, 'SIZE_%s' % attr.upper())
            return self.display(*size)
        except:
            return getattr(super(Image, self), attr)

    def display_url(self, size_spec, upscale=False):
        """ convenience method for the pic attribute's method of same name """
        if self.crop_x and self.crop_y and self.crop_side:
            return self.pic.display_url(size_spec, (self.crop_x, self.crop_y, self.crop_side), upscale=upscale)
        else:
            return self.pic.display_url(size_spec, None, upscale=upscale)

    def absolute_url(self):
        """ convenience method for the pictures absolute url """
        return "%s%s" % (settings.MEDIA_URL, self.pic)
        
    def crop_thumb(self, size_spec, crop_coords):
        """ convenience method for the pic attribute's method of same name """
        self.crop_x = crop_coords[0]
        self.crop_y = crop_coords[1]
        self.crop_side = crop_coords[2] - crop_coords[0]
        self.pic.crop_thumb(size_spec, crop_coords)

    def delete_old_thumbs(self):
        """ convenience method for pic's attribute of same name"""
        self.pic.delete_old_thumbs()

    def __unicode__(self):
        return self.kicker

    def identifier(self):
        return make_url_friendly(self.kicker)

    def admin_thumb(self):
        """HTML for tiny thumbnail in the admin page."""
        return """<img src="%s">""" % self.display_url(Image.SIZE_TINY)
    admin_thumb.allow_tags = True

class Gallery(Content):
    """
    A collection of displayed content (images, youtube, infographics, etc.)
    """

    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    contents = models.ManyToManyField(Content, through='GalleryMembership',
        related_name="galleries_set")

    objects = ContentManager()

    @property
    def img_title(self):
        """Title/alt for an <img> tag"""
        return self.title

    def display_url(self, size_spec, upscale=False):
        if self.cover_image is None:
            return ''
        return self.cover_image.display_url(size_spec)

    @property
    def cover_image(self):
        # TODO: clear this on save
        if not hasattr(self, '_cover_image'):
            if not self.contents.all():
                ci = None
            else:
                ci = self.contents.order_by('galleries_set')[0].child
            self._cover_image = ci
        return self._cover_image

    @property
    def admin_contents(self):
        acrs = GalleryMembership.objects.filter(gallery=self)
        return [x.content.child for x in acrs]

    @property
    def admin_content_pks(self):
        acrs = GalleryMembership.objects.filter(gallery=self)
        return ";".join([str(x.content.pk) for x in acrs])

    def __unicode__(self):
        return self.title

    def delete(self):
        self.contents.clear()
        super(Gallery, self).delete()

    class Meta:
        verbose_name_plural = "Galleries"


class GalleryMembership(models.Model):
    gallery = models.ForeignKey(Gallery, related_name="gallery_set")
    content = models.ForeignKey(Content, related_name="content_set")
    order = models.IntegerField()

    class Meta:
        ordering = ('order',)


def youtube_get_save_path(instance, filename):
    ext = splitext(filename)[1]
    filtered_capt = make_file_friendly(instance.slug)
    if filtered_capt == '':
        filtered_capt = make_file_friendly(instance.title)
    return datetime.now().strftime("photos/%Y/%m/%d/%H%M%S_") + \
        filtered_capt + ext

class YouTubeVideo(Content):
    """Embeddable YouTube video."""

    key = models.CharField(blank=False, null=False, max_length=100,
        help_text="youtube.com/watch?v=(XXXXXX)&... part of the YouTube URL. "
        "NOTE: THIS IS NOT THE ENTIRE YOUTUBE URL.",
        db_index=True)
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    pic = SuperImageField('Preview Picture', max_width=960,
        upload_to=youtube_get_save_path, null=True)

    objects = ContentManager()

    @property
    def img_title(self):
        """Title/alt for <img> tags."""
        return self.title

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name_plural = "YouTube Videos"

    def display_url(self, size_spec, upscale=False):
        if self.pic:
            return self.pic.display_url(size_spec, upscale=upscale)
        else:
            return ''

    @property
    def youtube_url(self):
        return 'http://www.youtube.com/watch?v=%s' % self.key

    def admin_youtube(self):
        return '<a href="%s">%s</a>' % (self.youtube_url, self.youtube_url)
    admin_youtube.allow_tags = True
    admin_youtube.short_description = 'YouTube Link'

    def admin_thumb(self):
        """HTML for tiny thumbnail in the admin page."""
        if self.pic:
            return """<img src="%s">""" % self.pic.display_url(Image.SIZE_TINY)
        else:
            return "No Preview"
    admin_thumb.allow_tags = True
    admin_thumb.short_description = 'Thumbnail'


def misc_get_save_path(instance, filename):
    ext = splitext(filename)[1]
    slug = make_file_friendly(instance.slug)
    return datetime.now().strftime("misc/%Y/%m/%d/%H%M%S_") + slug + ext

class FlashGraphic(Content):
    """A Flash Graphic."""

    graphic = models.FileField(upload_to=misc_get_save_path, null=False, blank=False)
    pic = SuperImageField(upload_to=misc_get_save_path, max_width=600,
        blank=False, null=False, storage=OverwriteStorage(),
        help_text='Thumbnail')
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)

    def __unicode__(self):
        return self.title

    objects = ContentManager()

    def display_url(self, size_spec, upscale=False):
        if self.pic:
            return self.pic.display_url(size_spec)
        else:
            return ''

    def admin_thumb(self):
        """HTML for tiny thumbnail in the admin page."""
        if self.pic:
            return """<img src="%s">""" % self.pic.display_url(Image.SIZE_TINY)
        else:
            return "No Preview"
    admin_thumb.allow_tags = True
    admin_thumb.short_description = 'Thumbnail'

    class Meta:
        verbose_name_plural = "Flash Graphics"


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

    def __unicode__(self):
        return self.title

    objects = ContentManager()

class Marker(models.Model):
    """
    Markers for a Google Map
    """
    map = models.ForeignKey(Map,related_name='markers')
    lat = models.FloatField(blank=False, db_index=True)
    lng = models.FloatField(blank=False, db_index=True)
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
        ('contrib', 'Contributing Writer'),
    )

    objects = ContentManager()

    headline = models.CharField(blank=False, max_length=127, db_index=True)
    subheadline = models.CharField(blank=True, null=True, max_length=255)
    byline_type = models.CharField(
        blank=True, null=True, max_length=70, choices=BYLINE_TYPE_CHOICES,
        help_text='This will automatically be pluralized if there ' \
             'are multiple contributors.')
    text = models.TextField(blank=False, null = False)
    teaser = models.CharField(
        blank=True, max_length=5000,
        help_text='If left blank, this will be the first sentence ' \
                    'of the article text.'
    )
    page = models.CharField(blank=True, null=True, max_length=10,
        help_text='Page in the print edition.')
    proofer = models.ForeignKey(
        Contributor, related_name='proofed_article_set',
        limit_choices_to={'is_active': True}, blank=True, null=True)
    sne = models.ForeignKey(
        Contributor, related_name='sned_article_set',
        limit_choices_to={'is_active': True}, blank=True, null=True)
    web_only = models.BooleanField(default=False, null=False, blank=False)

    rel_content = models.ManyToManyField(Content, through='ArticleContentRelation',
        null=True, blank=True, related_name="rel_content")

    @property
    def rel_admin_content(self):
        acrs = ArticleContentRelation.objects.filter(article=self)
        return ";".join([str(x.related_content.pk) for x in acrs])

    # Override save to check whether we're modifying an existing article's text
    def save(self, *args, **kwargs):
        if self.pk:
            try:
                prev_article = Article.objects.get(pk=self.pk)
            except Article.DoesNotExist:
                prev_article = None
            if prev_article is not None and int(prev_article.pub_status) is 1:
                oldtext = prev_article.text
                # If the text has changed, make a new Correction for the old text
                if oldtext != self.text:
                    corr = Correction(text = oldtext, article = self)
                    corr.save()
        return super(Article, self).save(*args, **kwargs)

    def delete(self):
        self.rel_content.clear()
        super(Article, self).delete()

    @property
    def long_teaser(self):
        return sub(r'<[^>]*?>', '', truncatewords(self.title,50))

    @property
    def main_rel_content(self):
        r = self.rel_content.all()[:1]
        # need to return child, so that subclass methods can be called
        r = r[0].child if r else None
        return r if not isinstance(r, Article) else None

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
    rating = models.IntegerField(choices=RATINGS_CHOIES, db_index=True)
    article = models.ForeignKey(Article, null=True, blank=True)


class Score(models.Model):

    article = models.ForeignKey(Article,related_name='sports_scores')
    sport = models.ForeignKey(Tag,limit_choices_to={'category':'sports'},)
    opponent = models.CharField(max_length=50, null=True, blank=True)
    our_score = models.CharField(max_length=20, null=True, blank=True)
    their_score = models.CharField(max_length=20, null=True, blank=True)
    home_game = models.BooleanField()
    text = models.CharField(max_length=50, null=True, blank=True)
    event_date = models.DateField()

    def __unicode__(self):
        if self.text:
            return self.text
        elif self.opponent and self.home_game:
            return "Harvard %s %s %s" % (self.our_score,self.opponent,self.their_score)
        elif self.opponent and self.home_game:
            return "%s %s Harvard %s" % (self.opponent,self.their_score,self.our_score)


class Correction(models.Model):
    text = models.TextField(blank=False, null=False)
    dt = models.DateTimeField(auto_now=True, db_index=True)
    article = models.ForeignKey(Article, null=False, blank=False)

    def save(self, *args, **kwargs):
        return super(Correction, self).save(*args, **kwargs)

    def __unicode__(self):
        return str(self.id)

def genericfile_get_save_path(instance, filename):
    ext = splitext(filename)[1]
    title = make_file_friendly(instance.title)
    return datetime.now().strftime("misc/genfiles/%Y/") + title + ext


class GenericFile(models.Model):
    """A Generic File (pdf/random thing on a form/etc.)."""

    gen_file = models.FileField(upload_to=genericfile_get_save_path, null=False, blank=False, verbose_name="File")
    title = models.CharField(blank=False, null=False, max_length=200)
    description = models.TextField(blank=False, null=False)
    created_on = models.DateTimeField(auto_now_add=True, db_index=True)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Generic Files"
        
class MostReadArticles(models.Model):
    create_date = models.DateTimeField(auto_now=True)
    article1 = models.ForeignKey(Article, null=False, blank=False, related_name="MostReadArticle1")
    article2 = models.ForeignKey(Article, null=False, blank=False, related_name="MostReadArticle2")
    article3 = models.ForeignKey(Article, null=False, blank=False, related_name="MostReadArticle3")
    article4 = models.ForeignKey(Article, null=False, blank=False, related_name="MostReadArticle4")
    article5 = models.ForeignKey(Article, null=False, blank=False, related_name="MostReadArticle5")

def package_pic_path(instance, filename):
    ext = splitext(filename)[1]
    title = instance.title.replace(" ","")
    
    name = '%s' % \
        (title)
    return 'photos/' + name + ext
    
class FeaturePackage(models.Model):
    
    PUB_CHOICES = (
        (0, 'Draft'),
        (1, 'Published'),
        (-1, 'Deleted'),
    )
    
    title = models.CharField(blank=False, null=False, max_length=250)
    
    description = models.TextField(blank=False, null=False)
    
    pub_status = models.IntegerField(null=False, choices=PUB_CHOICES,
        default=0, db_index=True)
        
    create_date = models.DateTimeField(auto_now_add=True)
    
    edit_date = models.DateTimeField(auto_now=True)
    
    #indicates where or not a big banner should appear on the index page
    feature =  models.BooleanField(default=False)
    
    slug = models.CharField(blank=True, null=False, max_length=250)
    
    banner = SuperImageField(blank=True, null=True, max_width=550,
        upload_to=package_pic_path, storage=OverwriteStorage())
        
    class Meta:
        permissions = (
            ('content.can_publish', 'Can publish content',),
            ('content.can_unpublish', 'Can unpublish content',),
            ('content.can_delete_published', 'Can delete published content'),
        )

class FeaturePackageSection(models.Model):

    PUB_CHOICES = (
        (0, 'Draft'),
        (1, 'Published'),
        (-1, 'Deleted'),
    )
    
    LAYOUT_CHOICES = (
        (0, 'Normal'),
        (1, 'Media'),
        (2, 'No Video'),
    )
    
    title = models.CharField(blank=False, null=False, max_length=100)
    
    create_date = models.DateTimeField(auto_now_add=True)
    
    edit_date = models.DateTimeField(auto_now=True)
    
    icon = SuperImageField(blank=True, null=True, max_width=150,
        upload_to=package_pic_path, storage=OverwriteStorage())
        
    pub_status = models.IntegerField(null=False, choices=PUB_CHOICES,
        default=0, db_index=True)
        
    layout = models.IntegerField(null=False, choices=LAYOUT_CHOICES,
        default=0, db_index=True)
        
    slug = models.CharField(blank=True, null=False, max_length=250)
    
    sideStories = models.IntegerField(null=False, default=6, verbose_name='Number of Side Stories', 
        help_text='This is the number of stories that will appear on the right hand column for this section. These will be the last x stories selected in the related content. IE. if you put 6 here, the last 6 stories selected below will be used on the side')
    
    sideBarUpperTitle = models.CharField(blank=True, null=False, max_length=250, verbose_name='Side bar Upper Title')
    
    sideBarLowerTitle = models.CharField(blank=True, null=False, max_length=250, verbose_name='Side bar Lower Title')
    
    MainPackage = models.ForeignKey(FeaturePackage, null=False, blank=False, related_name="sections")
    
    related_contents = models.ManyToManyField(Content, null=True, related_name="related_contents", through='PackageSectionContentRelation')
    
    @property
    def rel_admin_content(self):
        acrs = PackageSectionContentRelation.objects.filter(FeaturePackageSection=self)
        return ";".join([str(x.related_content.pk) for x in acrs])
    
    class Meta:
        permissions = (
            ('content.can_publish', 'Can publish content',),
            ('content.can_unpublish', 'Can unpublish content',),
            ('content.can_delete_published', 'Can delete published content'),
        )
    
class PackageSectionContentRelation(models.Model):
    FeaturePackageSection = models.ForeignKey(FeaturePackageSection, related_name = "fps")
    related_content = models.ForeignKey(Content)
    order = models.IntegerField(blank=True, null=True)
    isFeatured = models.BooleanField(default=False)

    class Meta:
        ordering = ('order',)
