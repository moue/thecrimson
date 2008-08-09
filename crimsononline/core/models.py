from hashlib import md5
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User, Group

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
        elif name == 'boards':
            # INCORRECT BEHAVIOR: this stuff should only happen on save, not on a setattr
            # also, this is a hack; this only works because boards happens to get set last
            groups = [board.group for board in value]
            if self.user == None and groups != []:
                u = User()
                if not self.class_of:
                    self.class_of = 0
                u.username = ('%s_%s_%s_%d' % (
                    self.first_name,
                    self.middle_initial,
                    self.last_name,
                    self.class_of
                ))[:30]
                u.set_unusable_password() #auth is done with Harvard PIN
                u.is_staff = True
                u.save()
                self.user = u
            if self.user != None:
                self.user.groups = groups
                self.user.save()
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
    
    web_only = models.BooleanField(default=False,
                                    help_text='Check if this issue has no corresponding print edition.')
    web_publish_date = models.DateTimeField(blank=False,
                                            help_text='When this issue goes live (on the web).')
    issue_date = models.DateField(blank=False,  
                                    help_text='Corresponds with date of print edition.')
    comments = models.TextField(blank=True, 
                                null=True,
                                help_text='Notes about this issue.')
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
    
    caption = models.CharField(blank=False, max_length=1000)
    kicker = models.CharField(blank=False, max_length=500)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    contributor = models.ForeignKey(Contributor)
    tags = models.ManyToManyField(Tag)

    def __unicode__(self):
        return "Image"

class ImageFile(models.Model):
    """The actual file of an Image"""
    
    image = models.ForeignKey(Image)
    size = models.CharField(blank=False, max_length=20)
    location = models.CharField(blank=False, max_length=500)

    def __unicode__(self):
        return self.location
        
class ImageGallery(models.Model):
    """A collection of Images"""

    images = models.ManyToManyField(Image)
    cover_image = models.ForeignKey(Image, related_name='cover_images')
    created_on = models.DateField(auto_now_add=True)

    def __unicode__(self):
        return "ImageGallery"

class PublishedArticlesManager(models.Manager):
    """Articles Manager that only returns published articles"""
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set().filter(is_published=True)

class Article(models.Model):
    """Non serial text content"""

    BYLINE_TYPE_CHOICES = (
        ('cstaff', 'Crimson Staff Writer'),
    )

    headline = models.CharField(blank=False, 
                                max_length=70, 
                                unique_for_date='uploaded_on')
    subheadline = models.CharField(blank=True, null=True, max_length=70)
    byline_type = models.CharField(blank=True,
                                    null=True,
                                    max_length=70, 
                                    choices=BYLINE_TYPE_CHOICES)
    text = models.TextField(blank=False)
    teaser = models.CharField(blank=True, 
                                max_length=1000,
                                help_text='If left blank, this will be the first sentence of the article text.')
    contributors = models.ManyToManyField(Contributor)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(default=0,
                                    help_text='Higher priority articles show up at the top of the home page.')
    page = models.CharField(blank=True, null=True, max_length=10)
    proofer = models.ForeignKey(Contributor, related_name='proofed_article_set')
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
    