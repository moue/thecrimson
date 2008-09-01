from django.db import models

class ContentModule(models.Model):
    """A location for content"""
    url = models.CharField(blank=False, null=False, max_length=100)
    page_loc = models.IntegerField(blank=False, null=False)
    default_content = models.ForeignKey(Content, blank=True, null=True)
    default_template = models.CharField(blank=True, null=True, max_length=100)
    default_view = models.CharField(blank=False, max_length=50)
    comment = models.CharField(blank=True, null=True, max_length=200)
    
    class Meta:
        unique_together = ('url', 'page_loc',)
    
    def __unicode__(self):
        return "ContentModule"
    


class Content(models.Model):
    """User editable HTML content for a certain time span."""
    html = models.TextField(blank=False, null=False)
    goes_live = models.DateTimeField(blank=False, null=False)
    expires = models.DateTimeField(blank=False, null=False)
    content_module = models.ForeignKey(ContentModule)
    
    def __unicode__(self):
        return "Content"
    
