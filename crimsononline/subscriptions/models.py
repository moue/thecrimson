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
            (domain, path[1:], self.pk, self.passcode)
        
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
    
    @staticmethod
    def send_all(issue_date=None):
        """Send all the email subscriptions."""
        for sub in EmailSubscription.objects.filter(is_active=True):
            sub.send(issue_date)
        
    
    def send(self, issue_date=None):
        """Send out this particular email subscription.
        
        Should fail if this subscription is inactive
        """
        if not self.is_active:
            return False
        if issue_date is None:
            issue_date = date.today()
        path = reverse("crimsononline.subscriptions.views.email_manage")
        d = {'issue_date': issue_date, 'subscription': self}
        domain = settings.URL_BASE
        if domain[-1] == '/':
            domain = domain[:-1]
        d['manage_url'] = u"%s%s?subscription_id=%s&passcode=%s" % \
                            (domain, path[1:], self.pk, self.passcode)
        articles = content.Article.objects.filter(issue__issue_date=issue_date)
        d['top_stories'] = articles.filter(priority__gt=5) \
                           if self.top_stories else []
        l = len(d['top_stories'])
        d['sections'] = dict([(s.name, articles.filter(section=s)) \
                              for s in self.sections.all()])
        l += sum([len(x) for x in d['sections']])
        d['tags'] = dict([(t.text, articles.filter(tags=s)) \
                          for t in self.tags.all()])
        l += sum([len(x) for x in d['tags']])
        d['contributors'] = dict([(str(c), articles.filter(tags=c)) \
                                  for c in self.contributors.all()])
        l += sum([len(x) for x in d['contributors']])
        # don't deliver mail if there are no articles
        if l > 0:
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

PAPER_SUB_TYPES = (
    (0, 'Biweekly'),
    (1, 'Premium'),
    (2, 'Premium Plus'),    
)
PAPER_START_DATES = (
    (0, 'September/October'),
    (1, 'November/December'),
    (2, 'January/February'),
    (3, 'March/April'),
    (4, 'May'),
    (5, 'Fall Semester'),
    (6, 'Spring Semester'),
)
        
class PaperSubscription(models.Model):
    sub_type = models.IntegerField(choices=PAPER_SUB_TYPES, verbose_name="Subscription Type")
    start_period = models.IntegerField(choices=PAPER_START_DATES, verbose_name="Starting Time Period")
    price = models.DecimalField(max_digits=5, decimal_places = 2, verbose_name="Price")
    
    class Meta:
        verbose_name = "Paper Subscription"

    def __unicode__(self):
        act_promos = PaperPromoCode.objects.filter(subscription=self.pk, active=1).count()
        promo_text = ""
        if act_promos > 0:
            promo_text = "(%d active promotion%s)" % (act_promos, "s" if act_promos > 1 else "")
        return "%s, %s %s" % (PAPER_SUB_TYPES[self.sub_type][1], 
        PAPER_START_DATES[self.start_period][1],
        promo_text
        )
    
class PaperPromoCode(models.Model):
    class Meta:
        verbose_name = "Promotional Code"

    subscription = models.ForeignKey('PaperSubscription')
    code = models.CharField(max_length=25)
    price = models.DecimalField(max_digits=6, decimal_places = 2)
    active = models.BooleanField(default=1)
    
    def __unicode__(self):
        return "%s, discount from $%.2f to $%.2f" % (self.code, self.subscription.price, self.price)