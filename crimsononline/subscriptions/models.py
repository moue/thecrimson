import hashlib

from random import random
from datetime import datetime
from django.conf import settings
from django.db import models
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

def new_conf_code():
    return hashlib.md5(str(datetime.now()) + str(random())).hexdigest()

class Subscription(models.Model):
    email = models.EmailField(blank=False)
    contributors = models.ManyToManyField('content.Contributor', blank=True)
    sections = models.ManyToManyField('content.Section', blank=True)
    tags = models.ManyToManyField('content.Tag', blank=True)
    confirmation_code = models.CharField(max_length=50, default=new_conf_code)
    active = models.BooleanField(default=False)
    
    def send_confirmation(self):
        domain = settings.URL_BASE
        path = reverse("crimsononline.subscriptions.views.email_confirm")
        email_url = u"%s%s" % (domain, path[1:(len(path)-1)])
        
        context = {
            "email_url": email_url,
            "email_address": self.email,
            "confirmation_code": self.confirmation_code
        }
        
        subject = "Subscription Confirmation for The Harvard Crimson"
        body = render_to_string("email/email_body.txt", context)
        
        msg = EmailMessage(subject, body, "test@test.com", [self.email])
        msg.content_subtype = "html"  # Main content is now text/html
        msg.send()
        
        #send_mail(subject,body,'from@example.com',[self.email])
    
    def confirm(self, code):
        if code == self.confirmation_code:
            subject = "Subscription Confirmation for The Harvard Crimson"
            body = "Subscription confirmed!"
            #send_mail(subject, body, 'from@example.com', [self.email])
            self.confirmation_code = ''
            self.active = True
            self.save()
        return self.active
    
	def __unicode__(self):
		return self.email
    
