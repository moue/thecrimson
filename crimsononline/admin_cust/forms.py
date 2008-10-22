from django import forms
from django.conf import settings
from django.template.loader import render_to_string

class FbSelectWidget(forms.widgets.HiddenInput):
    """
    A widget that allows for multiple model selection, similar to Facebook's
    compose message To: field.
    
    Takes 4 additional named arguments
    url: 
    model: 
    labeler: 
    multiple: optional
    For explanations, see FbModelChoiceField's docstring
    """
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
        self.is_multiple = kwargs.pop('multiple', False)
        return super(FbSelectWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            if getattr(value, '__iter__', None):
                obj_list = self.model.objects.filter(pk__in=value)
                value = ','.join([str(v) for v in value])
            else:
                obj_list = [self.model.objects.get(pk=value)]
            objs = {}
            for obj in obj_list:
                objs[obj.pk] = self.labeler(obj)
        hidden = super(FbSelectWidget, self).render(name, value, attrs)
        url, is_multiple = self.url, self.is_multiple
        return render_to_string("widgets/fb_select_multiple.html", locals())
        
class FbModelChoiceField(forms.CharField):
    """
    A model multiple choice field that uses a Facebook-like autocomplete
    interface / widget.
    
    This field is bound to the FbSelectMultiple Widget.
    
    Takes 4 additioal name arguments:
    multiple: select multiple objects at once? False by default
    model: the model from which to select multiple
    url: the widget makes a AJAX requests for autocompletion. this is the
        url that returns the autcomplete search results. the request is made
        to the url: url?q=query_string&limit=max_results
        the results should be returned as text, with one result on each
        line. each results should look like: primary_key|label
    labeler: a function that takes a model object and returns a label.
        this is used for the initial labels.
    """
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        self.is_multiple = 1 if kwargs.pop('multiple', False) else 0
        kwargs['widget'] = FbSelectWidget(url=kwargs.pop('url'), 
            model=self.model, labeler=kwargs.pop('labeler'),
            multiple=self.is_multiple)
        return super(FbModelChoiceField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError("This can't be left blank")
            return
        try:
            pks = [int(v) for v in value.split(',') if v]
            # only is_multiple variants of this should have multiple pks
            if len(pks) > 1 and not self.is_multiple:
                raise forms.ValidationError("Something terrible happened!")
            objs = self.model.objects.filter(pk__in=pks)
            if objs and not self.is_multiple:
                objs = objs[0]
            return objs
        except ValueError:
            # not a normal validation error, since the front end
            # should guarantee valid results. also, users can't
            # manually put values in, so a real validation error
            # wouldn't be helpful.
            raise forms.ValidationError("Something terrible happened!")
         