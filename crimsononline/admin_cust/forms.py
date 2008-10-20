from django import forms
from django.conf import settings
from django.template.loader import render_to_string

class FbSelectMultipleWidget(forms.widgets.HiddenInput):
    class Media:
        js = ("/site_media/scripts/framework/jquery.bgiframe.min.js",
            "/site_media/scripts/framework/jquery.dimensions.js",
            "/site_media/scripts/framework/jquery.autocomplete.js",
            "/site_media/scripts/framework/jquery.autocompletefb.js",)
        css = {'all': ("/site_media/css/framework/jquery.autocompletefb.css",)}
    
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        self.model = kwargs.pop('model')
        self.labeler = kwargs.pop('labeler')
        return super(FbSelectMultipleWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            if getattr(value, '__iter__', None):
                obj_list = self.model.objects.filter(pk__in=value)
                value = ','.join([str(v) for v in value])
            else:
                obj_list = [self.model.objects.get(pk=pk)]
            objs = {}
            for obj in obj_list:
                objs[obj.pk] = self.labeler(obj)
        hidden = super(FbSelectMultipleWidget, self).render(name, value, attrs)
        url = self.url
        return render_to_string("widgets/fb_select_multiple.html", locals())
        
class FbModelMultipleChoiceField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        kwargs['widget'] = FbSelectMultipleWidget(url=kwargs.pop('url'), 
            model=self.model, labeler=kwargs.pop('labeler'))
        super(FbModelMultipleChoiceField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            return
        try:
            pks = [int(v) for v in value.split(',') if v]
            return self.model.objects.filter(pk__in=pks)
        except ValueError:
            # not a normal validation error, since the front end
            # should guarantee valid results. also, users can't
            # manually put values in, so a real validation error
            # wouldn't be helpful.
            raise forms.ValidationError("Something terrible happened!")
         