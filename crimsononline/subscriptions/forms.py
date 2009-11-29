from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import *
from crimsononline.common.forms import FbModelChoiceField, FbSelectWidget
from crimsononline.content.models import Contributor, Tag, Section
from crimsononline.subscriptions.models import EmailSubscription, PaperSubscription, PAPER_SUB_TYPES

class EmailSubscribeForm(forms.ModelForm):
    contributors = FbModelChoiceField(required=False, multiple=True, 
        model=Contributor, url='/subscribe/email/ajax/fb_find/contributor/', 
        no_duplicates=True)
    top_stories = forms.BooleanField(label="Top Stories")
    tags = FbModelChoiceField(required=False, multiple=True, model=Tag,
        url='/subscribe/email/ajax/fb_find/tag/', no_duplicates=True)
    sections = forms.ModelMultipleChoiceField(Section.all(), 
        widget=forms.CheckboxSelectMultiple, required=False)
    email = forms.EmailField(required=True, label="Your Email",
                             widget=forms.TextInput(attrs={'size':'60'}))
    
    class Media:
        css = FbSelectWidget.Media.css
        js = FbSelectWidget.Media.js
    
    class Meta:
        model = EmailSubscription
        fields = ('email', 'sections', 'contributors', 'tags', 'top_stories')
    
    def clean(self):
        d = self.cleaned_data
        # have to pick something
        if d and not (d.get('contributors', None) or d.get('tags', None) \
            or d.get('sections', None) or d.get('top_stories', None)):
            raise forms.ValidationError('You have to pick something '
                'to sign up for.')
        return self.cleaned_data
    

class EmailSubscriptionManageForm(EmailSubscribeForm):
    id = forms.IntegerField(widget=forms.HiddenInput)
    passcode = forms.CharField(widget=forms.HiddenInput)
    email = forms.EmailField(required=True, help_text='If you change your '
        'email address, you will need to reactivate your subscription by '
        'confirming your new email address.', 
        widget=forms.TextInput(attrs={'size':'60'}))
    
    class Meta:
        model = EmailSubscription
        fields = ('email', 'sections', 'contributors', 'tags', 'top_stories',
            'id', 'passcode',)
    

class EmailSubscribeConfirmForm(forms.Form):
    subscription_id = forms.IntegerField()
    passcode = forms.CharField(max_length=50)
    
    def clean(self):
        cleaned = self.cleaned_data
        if cleaned:
            try:
                s = EmailSubscription.objects.get(pk=cleaned['subscription_id'],
                    passcode=cleaned['passcode'])
            except EmailSubscription.DoesNotExist:
                raise forms.ValidationError('Subscription could not be found.')
            cleaned['email_subscription'] = s
        return cleaned
    
class PaperSubscribeForm(forms.ModelForm):
    class Meta:
        model = PaperSubscription
        fields = ('sub_type','start_period',)
