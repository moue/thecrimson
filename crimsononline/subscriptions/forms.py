from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import *
from crimsononline.common.forms import FbModelChoiceField, FbSelectWidget
from crimsononline.content.models import Contributor, Tag, Section
from crimsononline.subscriptions.models import Subscriber

class SubscribeForm(UserCreationForm):
    username = forms.EmailField(label="Email Address")

    contributors = FbModelChoiceField(required=False, multiple=True, 
        model=Contributor, url='/subscribe/email/ajax/fb_find/contributor/', 
        no_duplicates=True)
    tags = FbModelChoiceField(required=False, multiple=True, model=Tag,
        url='/subscribe/email/ajax/fb_find/tag/', no_duplicates=True)
    sections = forms.ModelMultipleChoiceField(Section.all(), 
        widget=forms.CheckboxSelectMultiple, required=False)
        
    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            Subscriber.objects.get(username=username)
        except Subscriber.DoesNotExist:
            return username
        raise forms.ValidationError("A subscriber wtih that email address already exists.")

    def save(self, commit=True):
        subscriber = super(SubscribeForm, self).save(commit=False)
        subscriber.email = subscriber.username
        subscriber.set_password(self.cleaned_data["password1"])
        subscriber.is_active = False
        if commit:
            subscriber.save()
        subscriber.send_confirmation()
        return subscriber
    
    class Media:
        css = FbSelectWidget.Media.css
        js = FbSelectWidget.Media.js
    
    class Meta:
        model = Subscriber
        fields = ('username','password1','password2', 'sections', 'contributors', 'tags',)
        

        
class SubscribeManageForm(forms.Form):
    sub = forms.IntegerField(widget=forms.HiddenInput, required=True)
    contributors = FbModelChoiceField(required=False, multiple=True, 
        model=Contributor, url='/subscribe/email/ajax/fb_find/contributor/', 
        no_duplicates=True)
    tags = FbModelChoiceField(required=False, multiple=True, model=Tag,
        url='/subscribe/email/ajax/fb_find/tag/', no_duplicates=True)
    sections = forms.ModelMultipleChoiceField(Section.all(), 
        widget=forms.CheckboxSelectMultiple, required=False)
        
    
    class Media:
        css = FbSelectWidget.Media.css
        js = FbSelectWidget.Media.js
    
    class Meta:
        model = Subscriber
        fields = ('sub','sections', 'contributors', 'tags',)
        
    def save(self):
        sub = Subscriber.objects.get(pk=self.cleaned_data["sub"])
        sub.contributors = self.cleaned_data["contributors"]
        sub.tags = self.cleaned_data["tags"]
        sub.sections = self.cleaned_data["sections"]
        sub.save()
        return sub
        
class SubscribeLoginForm(AuthenticationForm):
    pass
        
class SubscribeConfirmForm(forms.ModelForm):
    email = forms.EmailField()
    confirmation_code = forms.CharField(max_length=50)
    
    class Meta:
        model = Subscriber
        fields = ('email','confirmation_code')