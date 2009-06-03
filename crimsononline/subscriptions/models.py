import hashlib
from random import random
from datetime import datetime
from django.db import models

def new_conf_code():
    return hashlib.md5(str(datetime.now()) + str(random())).hexdigest()

class Subscription(models.Model):
    email = models.EmailField(blank=False)
    contributors = models.ManyToManyField('content.Contributor', blank=True)
    sections = models.ManyToManyField('content.Section', blank=True)
    tags = models.ManyToManyField('content.Tag', blank=True)
    confirmation_code = models.CharField(max_length=50, default=new_conf_code)
    active = models.BooleanField(default=False)
    
    def confirm(self, code):
        if code == self.confirmation_code:
            # TODO: send a confirmation email
            self.confirmation_code = ''
            self.active = True
            self.save()
        return self.active
    
	def __unicode__(self):
		return self.email
    
