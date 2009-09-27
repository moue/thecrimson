import hashlib
from random import random
from datetime import datetime, date

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.core.urlresolvers import reverse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string

from crimsononline.content import models as content

def new_conf_code():
    return hashlib.md5(str(datetime.now()) + str(random())).hexdigest()

class EmailSubscription(models.Model):
    """Subscription delivered via email.
    
    EmailSubscriptions start out inactive, but can be activated by 
    putting visiting the passcode page.  EmailSubscriptions should
    be administered on a page authenticated by the passcode.  
    
    When we integrate users, they can be automatically activated and
    administered with user authentication.
    """
    # things this person is subscribing to
    contributors = models.ManyToManyField('content.Contributor', blank=True)
    sections = models.ManyToManyField('content.Section', blank=True)
    tags = models.ManyToManyField('content.Tag', blank=True)
    top_stories = models.BooleanField(default=False)
    
    email = models.EmailField(blank=False, null=False)
    is_active = models.BooleanField(default=False)
    passcode = models.CharField(max_length=100, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    
    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.passcode = new_conf_code()
            super(EmailSubscription, self).save(force_insert, force_update)
            self.send_confirmation()
        else:
            super(EmailSubscription, self).save(force_insert, force_update)
        
    
    def send_confirmation(self, send=True):
        domain = settings.URL_BASE
        path = reverse("crimsononline.subscriptions.views.email_confirm")
        confirmation_url = u"%s%s?subscription_id=%s&passcode=%s" % \
            (domain, path[1:-1], self.pk, self.passcode)
        
        context = {
            "confirmation_url": confirmation_url,
            "email_address": self.email,
            "confirmation_code": self.passcode
        }
        
        subject = "Subscription Confirmation for The Harvard Crimson"
        body = render_to_string("email/confirm_email.txt", context)
        
        if send:
            send_mail(subject, body, "subscriptions@thecrimson.com", 
            [self.email], fail_silently=False)
    
    def send(self, issue_date=None):
        """Send out this particular email subscription.
        
        Should fail if this subscription is inactive
        """
        if not self.is_active:
            return False
        if issue_date is None:
            issue_date = date.today()
        d = {'issue_date': issue_date, 'subscription': self}
        articles = content.Article.objects.filter(issue__issue_date=issue_date)
        d['top_stories'] = articles.filter(priority__gt=5) \
                           if self.top_stories else None
        d['sections'] = dict([(s.name, articles.filter(section=s)) \
                              for s in self.sections.all()])
        d['tags'] = dict([(t.text, articles.filter(tags=s)) \
                          for t in self.tags.all()])
        d['contributors'] = dict([(str(c), articles.filter(tags=c)) \
                                  for c in self.contributors.all()])
        msg = EmailMultiAlternatives("The Crimson's Daily", 
            render_to_string('email/email.txt', d), 
            'subscriptions@thecrimson.com', [self.email])
        msg.attach_alternative(render_to_string('email/email.html', d), 
            'text/html')
        msg.send()
    
    def new_code(self):
        """Give self a new passcode."""
        self.passcode = new_conf_code()
    
    def confirm(self, code):
        if code == self.passcode:
            self.is_active = True
            self.save()
        return self.is_active
    
    def __unicode__(self):
        return self.email
    

class Subscription(models.Model):
    TYPE_CHOICES = (
        ('1', 'Premium Plus'),
        ('2', 'Premium'),
        ('3', 'BiWeekly'),
    )
    MONTH_CHOICES = (
        ('9', 'Sep.-Oct.'),
        ('11', 'Nov.-Dec.'),
        ('1', 'Jan.-Feb.'),
        ('3', 'Mar.-Apr.'),
        ('5', 'May'),
    )
    PRICE_CHOICES = (
        ('1-9', '350.00'),
        ('1-11', '300.00'), 
        ('1-1', '250.00'),
        ('1-3', '200.00'),
        ('2-9', '250.00'),
        ('2-11', '225.00'),
        ('2-1', '175.00'),
        ('2-3', '125.00'),
        ('1-5', '75.00'),
        ('3-f', '60.00'),
        ('2-5', '50.00'),
        ('3-s', '30.00'),
    )
    SEMESTER_CHOICES = (
        ('f', 'Full Year'), 
        ('s', 'Semester'),
    )
    sub_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    start_date = models.CharField(max_length=10, choices=MONTH_CHOICES)
    price = models.CharField(max_length=10, choices=PRICE_CHOICES)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)

class PaperSubscription(Subscription):
    # Subscription to hard copy of paper.
    
    promo = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(blank=False, null=False)
    is_active = models.BooleanField(default=False)
    passcode = models.CharField(max_length=100, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    currentprice = models.CharField(max_length=100, null=True)
    
    #I put these in from email subscription in case something breaks without them
    def save(self, force_insert=False, force_update=False):
        if not self.pk:
            self.passcode = new_conf_code()
            super(PaperSubscription, self).save(force_insert, force_update)
            self.send_confirmation()
        else:
            super(PaperSubscription, self).save(force_insert, force_update)    
    def new_code(self):
        """Give self a new passcode."""
        self.passcode = new_conf_code()
    
    def confirm(self, code):
        if code == self.passcode:
            self.is_active = True
            self.save()
        return self.is_active
    def __unicode__(self):
        return self.email