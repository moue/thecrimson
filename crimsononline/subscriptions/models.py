import hashlib

from random import random
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from content import models as content

def new_conf_code():
    return hashlib.md5(str(datetime.now()) + str(random())).hexdigest()
    
    
class Subscriber(User):
    # things this person is subscribing to
    contributors = models.ManyToManyField('content.Contributor', blank=True)
    sections = models.ManyToManyField('content.Section', blank=True)
    tags = models.ManyToManyField('content.Tag', blank=True)
    
    def send_confirmation(self):
        domain = settings.URL_BASE
        path = reverse("crimsononline.subscriptions.views.email_confirm")
        email_url = u"%s%s" % (domain, path[1:(len(path)-1)])
        
        try:
            reg = SubscriberRegistration.objects.get(subscriber=self)
        except:
            reg = SubscriberRegistration(subscriber=self)
            reg.save()
         
        context = {
            "email_url": email_url,
            "email_address": self.email,
            "confirmation_code": reg.confirmation_code
        }
        
        subject = "Subscription Confirmation for The Harvard Crimson"
        body = render_to_string("email/email_body.txt", context)
        
        send_mail(subject, body, "subscriptions@thecrimson.com",[self.email],fail_silently=False)
        
    def confirm(self, code):
        sr = SubscriberRegistration.objects.get(subscriber=self)
        if code == sr.confirmation_code:
            subject = "Subscription Confirmation for The Harvard Crimson"
            body = "Subscription confirmed!"
            self.is_active = True
            sr.delete()
            self.save()
        return self.is_active
        
	def __unicode__(self):
		return self.email

class SubscriberRegistration(models.Model):
    confirmation_code = models.CharField(max_length=50, default=new_conf_code)
    subscriber = models.ForeignKey(Subscriber)
