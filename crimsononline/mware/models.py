from django.db import models
from crimsononline.content.models import Content
from django.core.cache import cache

class SuperCrisis(models.Model):
    content = models.ForeignKey(Content)

    def __unicode__(self):
        return self.content.__unicode__()
   
    def delete(self):
        cache.set('crimsononline.supercrisismode', None)
        return super(SuperCrisis, self).delete()