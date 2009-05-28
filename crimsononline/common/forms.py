"""
Form things that would be useful across apps and models.  
This probably means only widgets and fields.
"""

from django import forms
from django.contrib import admin
from django.template.loader import render_to_string

class MaskedValueTextInput(forms.widgets.TextInput):
    def __init__(self, *args, **kwargs):
        self.sentinel = kwargs.pop('sentinel', '***')
        return super(MaskedValueTextInput, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            value = self.sentinel
        return super(MaskedValueTextInput, self).render(name, value, attrs)
    

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
            "/site_media/scripts/framework/jquery.autocomplete.js",
            "/site_media/scripts/framework/jquery.autocompletefb.js",
            "/site_media/scripts/framework/jquery.tooltip.pack.js",)
        css = {'all': ("/site_media/css/framework/jquery.autocompletefb.css",
                "/site_media/css/framework/jquery.tooltip.css",)}
    
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        self.model = kwargs.pop('model')
        self.labeler = kwargs.pop('labeler')
        self.is_multiple = kwargs.pop('multiple', False)
        self.no_duplicates = kwargs.pop('no_duplicates', True)
        # to fool the RelatedFieldWrapper
        self.choices = []
        return super(FbSelectWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            if isinstance(value, unicode) or isinstance(value, str):
                value = [int(v) for v in value.split(',') if v]
            if getattr(value, '__iter__', None):
                obj_list = self.model.objects.filter(pk__in=value)
                value = ','.join([str(v) for v in value])
            else:
                obj_list = [self.model.objects.get(pk=value)]
            objs = {}
            for obj in obj_list:
                objs[obj.pk] = self.labeler(obj)
        hidden = super(FbSelectWidget, self).render(name, value, attrs)
        url, is_multiple, no_dupes = self.url, self.is_multiple, self.no_duplicates
        return render_to_string("forms/fb_select_widget.html", locals())
    


class FbModelChoiceField(forms.CharField):
    """
    A model multiple choice field that uses a Facebook-like autocomplete
    interface / widget.
    
    This field is bound to the FbSelectMultiple Widget.
    
    Takes 6 additional named arguments:
    multiple: select multiple objects at once? False by default
    model: the model from which to select multiple
    @url: the widget makes a AJAX requests for autocompletion. this is the
        url that returns the autcomplete search results. the request is made
        to the url: url?q=query_string&limit=max_results
        the results should be returned as text, with one result on each
        line. each results should look like: primary_key|label
    @labeler: a function that takes a model object and returns a label.
        this is used for the initial labels.
    @no_duplicates: is true, AJAX query will tack on the parameter
        exclude, with value a list of values to exclude in the autosuggest.
        eg: url?q=fasman&limit=10&exclude=4,1,2
    @add_rel: the relation object? required for the "add related" button.
        None by default. If you set this, you also need to set admin_site.
    @admin_site: the admin site instance.  Required if @add_rel is defined.  
        None by default.
    """
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        # we use 1 and 0, since these get passed into JS, which doesn't
        #  like Python's capitalized True / False values
        self.is_multiple = 1 if kwargs.pop('multiple', False) else 0
        no_dupes = 1 if kwargs.pop('no_duplicates', True) else 0
        kwargs['widget'] = FbSelectWidget(
            url=kwargs.pop('url'), 
            model=self.model, 
            labeler=kwargs.pop('labeler'),
            multiple=self.is_multiple, 
            no_duplicates=no_dupes,
        )
        self.add_rel = kwargs.pop('add_rel', None)
        # if add_rel, use the related field widget wrapper for the add button
        if self.add_rel:
            kwargs['widget'] = admin.widgets.RelatedFieldWidgetWrapper(
                kwargs['widget'], self.add_rel, kwargs.pop('admin_site'))
        # just in case admin_site is still on there
        kwargs.pop('admin_site', None)
        s = super(FbModelChoiceField, self).__init__(*args, **kwargs)
        self.help_text = "Start typing; we'll provide suggestions.<br>%s" \
            % self.help_text
        return s
    
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


class SearchChoiceWidget(forms.widgets.HiddenInput):
    class Media:
        js = ('/site_media/scripts/framework/jquery-ui.packed.js',
            '/site_media/scripts/admin/widgets/SearchModelChoiceWidget.js',)
        css = {'all': ('/site_media/css/framework/jquery.ui.css',
            '/site_media/css/admin/SearchModelChoiceWidget.css'),}
    
    def __init__(self, *args, **kwargs):
        self.ajax_url = kwargs.pop('ajax_url', None)
        self.model = kwargs.pop('model', None)
        self.multiple = kwargs.pop('multiple', None)
        return super(SearchChoiceWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            if getattr(value, '__iter__', None):
                obj_list = list(self.model.objects.filter(pk__in=value))
                # sort them according to the order from value
                #  this will error if len(obj_list) < len(value)
                obj_list = dict([(o.pk, o) for o in obj_list])
                obj_list = [obj_list[v] for v in value]
                # turn value into a string, for rendering the hidden input
                value = ','.join([str(v) for v in value])
            else:
                try:
                    obj_list = [self.model.objects.get(pk=value)]
                except:
                    pass
        hidden = super(SearchChoiceWidget, self).render(name, value, attrs)
        ajax_url, multiple, model = self.ajax_url, self.multiple, self.model
        model_name = model.__name__
        return render_to_string("forms/search_select_widget.html", locals())
    


class SearchModelChoiceField(forms.CharField):
    """
    A model multiple choice field that uses a search and choose interface.
    Best for cases when the choice space is very large.
    Cleans into a list of or a single pk.
    
    You can supply your own widgets, but if you do, you should pass an
    instance of a widget in the @widget argument, not a widget class.
    Your widget should also have the 'multiple', 'ajax_url', and 'model'
    attributes, as this field will modify them.
    
    Takes 6 additional named arguments:
    @multiple: select multiple objects at once? False by default
    @model: the model from which to select multiple
    @ajax_url: the widget makes a AJAX requests for searching. this is the
        url that returns the search results
    @clean_to_objs: if true, clean returns objects; otherwise, returns pks
        (which doesn't require any additional db queries)
    @add_rel: the relation object? required for the "add related" button.
        None by default. If you set this, you also need to set admin_site.
    @admin_site: the admin site instance.  Required if @add_rel is defined.  
        None by default.
    """
    
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        self.clean_to_objs = kwargs.pop('clean_to_objs', False)
        # we use 1 and 0, since these get passed into JS, which doesn't
        #  like Python's capitalized True / False values
        self.multiple = 1 if kwargs.pop('multiple', False) else 0
        # if there's no widget provided, use the default
        if not kwargs.get('widget', None):
            kwargs['widget'] = SearchChoiceWidget()
        # modify the widget either way
        if kwargs.get('ajax_url'):
            kwargs['widget'].ajax_url = kwargs.pop('ajax_url')
        kwargs['widget'].model = self.model
        kwargs['widget'].multiple = self.multiple
        
        self.add_rel = kwargs.pop('add_rel', None)
        # if add_rel, use the related field widget wrapper for the add button
        if self.add_rel:
            kwargs['widget'] = admin.widgets.RelatedFieldWidgetWrapper(
                kwargs['widget'], self.add_rel, kwargs.pop('admin_site'))
        # just in case admin_site is still on there
        kwargs.pop('admin_site', None)
        return super(SearchModelChoiceField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError("This can't be left blank")
            return
        try:
            pks = [int(v) for v in value.split(',') if v]
            # only is_multiple variants of this should have multiple pks
            if len(pks) > 1 and not self.multiple:
                raise forms.ValidationError("Something terrible happened!")
            if self.clean_to_objs:
                objs = list(self.model.objects.filter(pk__in=pks))
                objs = dict([(o.pk, o) for o in objs])
                objs = [objs[v] for v in pks]
                return objs
            return pks
        except ValueError:
            # not a normal validation error, since the front end
            # should guarantee valid results. also, users can't
            # manually put values in, so a real validation error
            # wouldn't be helpful.
            raise forms.ValidationError("Something terrible happened!")
        



class CropWidget(forms.widgets.HiddenInput):
    """
    Widget for CropField
    """
    def __init__(self, *args, **kwargs):
        c = kwargs.pop('crop_size', None)
        self.crop_size = c
        self.display_size = kwargs.pop('display_size')
        self.aspect_ratio = float(c[0]) / float(c[1])
        self.image = None
        return super(CropWidget, self).__init__(*args, **kwargs)
    
    class Media:
        js = ('/site_media/scripts/framework/jquery.Jcrop.js',)
        css = {'all': ("/site_media/css/framework/jquery.Jcrop.css",)}
    
    def render(self, name, value, attrs=None):
        hidden = super(CropWidget, self).render(name, value, attrs)
        image = self.image
        return render_to_string("forms/crop_widget.html", locals())
    
    

class CropField(forms.CharField):
    """
    Field for cropping images
    
    Note: the form that uses this must inject the form's bound Image object
    into the widget's image attribute at run time
    TODO: make it so the above is not true
    
    @image => image instance
    @crop_size => a tuple locking down crop size
    """
    def __init__(self, *args, **kwargs):
        self.crop_size = kwargs.pop('crop_size', None)
        self.display_size = kwargs.pop('display_size', None)
        kwargs['widget'] = CropWidget(crop_size=self.crop_size, 
            display_size=self.display_size)
        return super(CropField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            return None
        "value should be a , separated quadruple corresponding to the cropbox"
        return tuple([int(i) for i in value.split(',')])