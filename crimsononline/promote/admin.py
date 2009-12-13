import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib import admin

from crimsononline.promote.models import WebCircCategory, WebCircContact, WebCirc
from crimsononline.common.forms import TinyMCEWidget

admin.site.register(WebCircCategory)
admin.site.register(WebCircContact)

class WebCircForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        r = kwargs.get('instance', None)
        super(WebCircForm, self).__init__(*args, **kwargs)
        if r is not None and r.sent_on:
            self.fields["send"].widget.attrs["disabled"] = 1
            self.fields["send"].help_text = "This WebCirc has already been sent"

    email_text = forms.fields.CharField(
        widget=TinyMCEWidget(attrs={'cols':'67','rows':'40'}), help_text=""
        "If you're copying and pasting from MS Word, please use the 'Paste "
        "From Word' button (with a little 'W' on it)"
    )
    send = forms.BooleanField(required=False)
    
    class Meta:
        model = WebCirc
    
class WebCircAdmin(admin.ModelAdmin):
    form = WebCircForm

    fieldsets = (
        ('General', {
            'fields': ('email_text','categories','send'),
        }),
        ('Extra', {
            'classes': ('collapse',),
            'fields': ('extra_contacts',),
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.save()
        send = form.cleaned_data["send"]
        if not obj.sent_on and send:
            #obj.sent_on = datetime.now()
            obj.send()
            

admin.site.register(WebCirc, WebCircAdmin)