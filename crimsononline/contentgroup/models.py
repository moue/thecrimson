from os.path import splitext
import string
from django.db import models
from django.core.cache import cache


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
    blurb = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=get_img_path, blank=True, null=True)
    
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
            cg = {}
            objs = ContentGroup().objects.all()[:]
            for obj in objs:
                cg[(obj.type, obj.name)] = obj
            cache.set('contentgroups_all', cg, 1000000)
        return cg.get((type, name), None)