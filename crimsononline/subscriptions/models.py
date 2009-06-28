import hashlib
from random import random
from datetime import datetime
from django.db import models
from django.core.mail import send_mail

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
        "SENDING CONFIRMATION!!!!"
        subject = "Subscription Confirmation for The Harvard Crimson"
        body = "Thanks for subscribing to The Harvard Crimson. To activate your subscription, please enter the code: '" \
            + self.confirmation_code + "' on your other tab"
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
    
