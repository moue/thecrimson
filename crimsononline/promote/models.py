from datetime import datetime

from crimsononline.content.models import *
from django.db import models
from django.core.mail import send_mail, EmailMultiAlternatives

class WebCircCategory(models.Model):
    category_name = models.CharField(max_length=100)
    description = models.TextField()
    
    class Meta:
        verbose_name = "WebCirc Category"

    def __unicode__(self):
        return self.category_name
            
class WebCircContact(models.Model):
    class Meta:
        verbose_name = "WebCirc Contact"

    contact_name = models.CharField(max_length=200)
    contact_person_name = models.CharField(max_length=200)
    email = models.EmailField()
    website = models.URLField()
    
    categories = models.ManyToManyField("WebCircCategory")

    def __unicode__(self):
        return "%s - %s" % (self.contact_name, self.email)
        
class WebCirc(models.Model):
    class Meta:
        verbose_name = "Send WebCirc"
    
    def __unicode__(self):
        if self.sent_on:
            return "WebCirc sent on %s" % self.sent_on.strftime("%B %d, %Y %I:%M%p")
        return "Unsent WebCirc"
    
    categories = models.ManyToManyField("WebCircCategory")
    extra_contacts = models.ManyToManyField("WebCircContact", blank=True)
    
    email_subject = models.CharField(max_length=200)
    email_text = models.TextField()
    sent_on = models.DateTimeField(null=True)
    
    def send(self):
        print "SENDING!!"
        names = set()
        for cat in self.categories.all():
            for cont in WebCircContact.objects.filter(categories=cat):
                names.add(cont)
        for extra in self.extra_contacts.all():
            names.add(extra)
         
        print self.categories.all()
        # mailmerge
        for name in names:
            nm = name.contact_person_name if name.contact_person_name else name.contact_name
            sal = "<p>Dear %s,</p>" % nm
            # todo: text version
            msg = EmailMultiAlternatives(self.email_subject, 
                sal + self.email_text, 
                'news@thecrimson.com', [name.email])
            msg.attach_alternative(sal + self.email_text,
                'text/html')
            msg.send()
