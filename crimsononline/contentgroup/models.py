from django.db import models
from os.path import splitext
import string


SAFE_CHARS = string.letters + string.digits
def filter_string(allowed_chars, str):
    return ''.join([c for c in str if c in allowed_chars])

def get_img_path(instance, filename):
    ext = splitext(filename)[1]
    safe_name = filter_string(SAFE_CHARS, instance.name)
    return "images/%s/%s.%s" % (instance.type, safe_name, ext)

class ContentGroup(models.Model):
    """
    Groupings of content.  Best for groupings that have simple metadata
        (just a blurb and an image), arbitrary (or chronological) ordering, 
        and not much else.
    This is different from tags because groupings have metadata.
    
    Examples:
      * Columns
      * Image Galleries ?
      * Blogs ?
      * Article Series (say, a series on Iraq or the election)
    """
    TYPE_CHOICES = (
        ('column', 'Column'),
        ('series', 'Series')
    )
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    name = models.CharField(max_length=25)
    blurb = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=get_img_path, blank=True, null=True)
    
    def __unicode__(self):
        return "%s/%s" % (self.type, self.name)
        