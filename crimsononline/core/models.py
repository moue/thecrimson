from hashlib import md5
from django.db import models
from django.db.models import permalink

class Contributor(models.Model):
    """Someone who contributes to the Crimson, like a staff writer or a photogarpher."""
    
    first_name = models.CharField(blank=False, max_length=70)
    last_name = models.CharField(blank=False, max_length=100)
    middle_initial = models.CharField(blank=True, null=True, max_length=1)
    created_on = models.DateField(auto_now_add=True)
    type = models.CharField(blank=True, null=True, max_length=100)
    profile_text = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.PhoneNumberField(blank=True, null=True)
    board = models.IntegerField(blank=False, null=False)
    class_of = models.IntegerField(blank=True, null=True)
    huid_hash = models.CharField(blank=True, null=True, max_length=255)
    is_active = models.BooleanField(default=True)

    def __unicode__(self):
        if self.middle_initial == None:
            m = ''
        else:
            m = ' ' + self.middle_initia
        return '%s%s %s' % (self.first_name, m, self.last_name)
        
    def __setattr__(self, name, value):
        # hash the huid before storing it
        if name == 'huid_hash' and value != None:
            value = md5(value).digest()
        super(Contributor, self).__setattr__(name, value)
    
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
    
    web_only = models.BooleanField(default=False)
    web_publish_date = models.DateTimeField(blank=False)
    issue_date = models.DateField(blank=False)

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

class Article(models.Model):
    """Non serial text content"""

    BYLINE_TYPE_CHOICES = (
        ('blank', ''),
        ('cstaff', 'Crimson Staff Writer'),
    )

    headline = models.CharField(blank=False, 
                                max_length=70, 
                                unique_for_date='uploaded_on')
    subheadline = models.CharField(blank=True, null=True, max_length=70)
    byline_type = models.CharField(blank=False, 
                                    max_length=70, 
                                    choices=BYLINE_TYPE_CHOICES)
    text = models.TextField(blank=False)
    teaser = models.CharField(blank=True, max_length=1000)
    contributors = models.ManyToManyField(Contributor)
    uploaded_on = models.DateField(auto_now_add=True)
    modified_on = models.DateField(auto_now=True)
    priority = models.IntegerField(default=0)
    page = models.CharField(blank=True, null=True, max_length=10)
    proofer = models.ForeignKey(Contributor, related_name='proofed_article_set')
    sne = models.ForeignKey(Contributor, related_name='sned_article_set')
    issue = models.ForeignKey(Issue)
    section = models.ForeignKey(Section)
    tags = models.ManyToManyField(Tag)
    image_gallery = models.ForeignKey(ImageGallery, null=True, blank=True)

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
    