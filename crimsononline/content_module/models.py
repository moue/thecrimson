from datetime import datetime, timedelta
from django.db import models
from django.utils.safestring import mark_safe

class ContentModule(models.Model):
    """A container for custom content"""
    url = models.CharField(blank=False, null=False, max_length=100)
    zone = models.IntegerField(blank=False, null=False)
    content = models.TextField(blank=True, null=True, 
        help_text='Type your content here. Use HTML.')
    default_content = models.TextField(blank=True, null=True,
        help_text='This content will show up after the current ' \
                    'content expires.')
    default_dict = models.TextField(blank=True, null=True, 
        help_text='Don\'t touch this unless you know what this is.')
    default_template = models.TextField(blank=True, null=True,
        help_text='Don\'t touch this unless you know what this is.')
    # default is a lambda because it needs to be a callable
    expiration = models.DateTimeField(blank=True, null=True, 
        default=lambda: datetime.now() + timedelta(days=2),
        help_text='If no one has updated this content module by this ' \
                    'time, it will revert to the default content.')
    comment = models.CharField(blank=True, null=True, max_length=200,
        help_text='No one outside the Crimson will see this.')
    
    class Meta:
        unique_together = ('url', 'zone',)
    
    def __unicode__(self):
        return self.url + '|' + str(self.zone)
    
    def render(self):
        #TODO: move the expiration code to something like cron
        if datetime.now() > self.expiration:
            self.content = None
            self.save()
        if self.content:
            return mark_safe(self.content)
        elif self.default_content:
            return mark_safe(self.default_content)
        elif self.default_dict and self.default_template:
            #TODO: unpickle, and render template
            pass
        else:
            return ''

