from django import forms
from crimsononline.common.forms import FbModelChoiceField, FbSelectWidget
from crimsononline.content.models import Contributor, Tag, Section
from crimsononline.subscriptions.models import Subscription

class EmailSubscriptionForm(forms.ModelForm):
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
        model = Subscription
        fields = ('email', 'sections', 'contributors', 'tags',)
    
class EmailConfirmSubscriptionForm(forms.ModelForm):
    email = forms.EmailField()
    confirmation_code = forms.CharField(max_length=50)
    
    class Meta:
        model = Subscription
        fields = ('email','confirmation_code')