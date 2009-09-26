"""
Form things that would be useful across apps and models.  
This probably means only widgets and fields.
"""

from os.path import split, exists, splitext
from PIL import Image as pilImage
from datetime import date

from django import forms
from django.contrib import admin
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile
from django.http import Http404
from django.template import defaultfilters as filter
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from crimsononline.content.models import *
from crimsononline.common.utils.numbers import reduce_fraction
from crimsononline.common.utils.misc import static_content

MONTHS = [(i, date(2009, i, 1).strftime('%B')) for i in range(1,13)]
DAYS = [(str(i), str(i)) for i in range(1, 32)]
YEARS = [(str(i), str(i)) for i in range(1900, (date.today().year) + 1)]
YEARS.reverse()

class DateSelectWidget(forms.widgets.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (forms.widgets.Select(choices=(MONTHS)), \
            forms.widgets.Select(choices=(DAYS)), \
            forms.widgets.Select(choices=(YEARS)))
        super(DateSelectWidget, self).__init__(widgets, attrs)
    

class RatingWidget(forms.widgets.RadioSelect):
    def __init__(self, *args, **kwargs):
        rr = kwargs.pop('ratings_range')
        kwargs['choices'] = [(str(r), str(r)) for r in rr]
        super(RatingWidget, self).__init__(*args, **kwargs)
    

class MaskedValueTextInput(forms.widgets.TextInput):
    def __init__(self, *args, **kwargs):
        self.sentinel = kwargs.pop('sentinel', '***')
        return super(MaskedValueTextInput, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            value = self.sentinel
        return super(MaskedValueTextInput, self).render(name, value, attrs)
    

class MaxSizeImageField(ImageField):
    """
    Image field with:
    * resizing to a maximum width and/or height
    """
    
    def __init__(self, verbose=None, max_width=None, max_height=None, **kwargs):
        self.width, self.height = max_width, max_height
        return super(MaxSizeImageField, self).__init__(verbose, **kwargs)
    
    def pre_save(self, model_instance, add):
        file = super(MaxSizeImageField, self).pre_save(model_instance, add)
        if file:
            img = pilImage.open(file.path)
            width = min(img.size[0], self.width) if self.width else None
            height = min(img.size[1], self.height) if self.height else None
            width = width or img.size[0]
            height = height or img.size[1]
            img.thumbnail((width, height), pilImage.ANTIALIAS)
            img.save(file.path)
        return file
    

def size_spec_to_size(size_spec, img_width, img_height):
    """
    converts a size_spec into actual image dimensions for the resulting image 
    """
    max_w, max_h, crop_w, crop_h = size_spec
    # set width / height constraints so we never upscale images
    max_w = min(img_width, max_w) if max_w else img_width
    max_h = min(img_height, max_h) if max_h else img_height
    
    if not crop_w:
        crop_w, crop_h = img_width, img_height
    
    h_ratio = float(max_h) / crop_h
    w_ratio = float(max_w) / crop_w
    ratio = min(h_ratio, w_ratio)
    
    max_w = int(ratio * crop_w)
    max_h = int(ratio * crop_h)
    
    return max_w, max_h

class AutosizeImageFieldFile(ImageFieldFile):
    """
    file attr_class, with additional wizardry for dynamically resizing images.
    keeps all resized images in the cache, to preserve disk space
    """
    def __init__(self, *args, **kwargs):
        ImageFieldFile.__init__(self, *args, **kwargs)
        self._url_cache, self._path_cache = {}, {}
    
    def crop_thumb(self, size_spec, crop_coords):
        """
        saves a cropped version of the file
        
        @size_spec => (max_width, max_height, crop_width, crop_height)
            crop_width and crop_height are relative to each other
        @crop_coords => x1,y1, x2, y2 tuple; represents upper left corner and 
            lower right corner of crop region
        """
        max_w, max_h, crop_w, crop_h = size_spec
        # set width / height constraints so we never upscale images
        max_w = min(self.width, max_w) if max_w else self.width
        max_h = min(self.height, max_h) if max_h else self.height
        
        # crop the file
        img = pilImage.open(self.path)
        img = img.transform(size_spec[:2], pilImage.EXTENT, crop_coords)
        
        new_path = self._get_path(size_spec)
        img.save(new_path)
        self._path_cache[size_spec] = new_path
    
    def display_path(self, size_spec):
        """returns the path for a sized image"""
        path = self._path_cache.get(size_spec, None)
        if path: return path
        path = self._get_path(size_spec)
        if not exists(path):
            img = pilImage.open(self.path)
            ht, wd = size_spec_to_size(size_spec, 
                self.width, self.height)
            # cropped image
            if size_spec[2] and size_spec[3]:
                # autogenerate crop_coordinates
                aspect_ratio = float(self.width) / float(self.height)
                crop_ratio = float(size_spec[2]) / size_spec[3]
                # extra space on left / right => preserve height
                if  aspect_ratio > crop_ratio:
                    w = int(self.height * crop_ratio)
                    crop_x1 = (self.width - w) / 2
                    crop_coords = (crop_x1, 0, crop_x1 + w, self.height)
                # extra space on top / bottom => preserve width
                elif aspect_ratio < crop_ratio:
                    h = int(self.width / crop_ratio)
                    crop_y1 = (self.height - h) / 2
                    crop_coords = (0, crop_y1, self.width, crop_y1 + h)
                else:
                    crop_coords = (0, 0, self.width, self.height)
                img = img.transform((ht, wd), pilImage.EXTENT, crop_coords)
            # constrained image
            else:
                img.thumbnail((ht, wd), pilImage.ANTIALIAS)
            img.save(path)
        self._path_cache[size_spec] = path
        return path
    
    def display_url(self, size_spec):
        """returns the path for a sized image"""
        url = self._url_cache.get(size_spec, None)
        if url: return url
        url = '%s/%s' % (split(self.url)[0], 
            split(self.display_path(size_spec))[1])
        self._url_cache[size_spec] = url
        return url
    
    def _get_path(self, size_spec):
        """
        calculates the path, no caching involved
        """
        path, ext = splitext(self.path)
        size = size_spec_to_size(size_spec, self.width, self.height)
        return path + "_%dx%d" % size + ext
    

class SuperImageField(ImageField):
    """
    just like super mario, this imagefield can run, jump, shoot fireballs,
        resize images on upload, overwrite existing images, 
        give you an autosizing image attribute, and fight bowser
    """
    attr_class = AutosizeImageFieldFile
    
    def __init__(self, verbose=None, max_width=None, max_height=None, **kwargs):
        self.width, self.height = max_width, max_height
        return super(SuperImageField, self).__init__(verbose, **kwargs)
    
    def pre_save(self, model_instance, add):
        file = super(SuperImageField, self).pre_save(model_instance, add)
        if file:
            img = pilImage.open(file.path)
            width = min(img.size[0], self.width) if self.width else None
            height = min(img.size[1], self.height) if self.height else None
            width = width or img.size[0]
            height = height or img.size[1]
            img.thumbnail((width, height), pilImage.ANTIALIAS)
            img.save(file.path)
        return file
    


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
        js = (static_content('scripts/framework/jquery.bgiframe.min.js'),
            static_content('scripts/framework/jquery.autocomplete.js'),
            static_content('scripts/framework/jquery.autocompletefb.js'),
            static_content('scripts/framework/jquery.tooltip.pack.js'),
            )
        css = {'all': (static_content('css/framework/jquery.autocompletefb.css'),
            static_content('css/framework/jquery.tooltip.css'))}
    
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        self.model = kwargs.pop('model')
        self.labeler = kwargs.pop('labeler')
        self.is_multiple = kwargs.pop('multiple', False)
        self.no_duplicates = kwargs.pop('no_duplicates', True)
        self.add_rel = kwargs.pop('add_rel', False)
        # to fool the RelatedFieldWrapper
        self.choices = []
        return super(FbSelectWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        if value:
            if isinstance(value, unicode) or isinstance(value, str):
                value = value.replace('[', '').replace(']', '')
                value = [int(v) for v in value.split(',') if v]
            if getattr(value, '__iter__', None):
                obj_list = self.model.objects.filter(pk__in=value)
                value = ','.join([str(v) for v in value])
            else:
                obj_list = [self.model.objects.get(pk=value)]
            objs = {}
            for obj in obj_list:
                objs[obj.pk] = self.labeler(obj)
        else:
            value = ''
        hidden = super(FbSelectWidget, self).render(name, value, attrs)
        url, is_multiple, no_dupes = self.url, self.is_multiple, self.no_duplicates
        return render_to_string("forms/fb_select_widget.html", locals())
    


def fbmc_search_helper(request):
    """
    A view function that parses the ajax query from the FBModelChoiceWidget
        and returns (query_string, exclude_list, limit)
        query_string: (what user typed into field),
        exclude_list: a list of excluded pks
        limit: limit on the number of items in the response
    
    Call this in your ajax processing views.  Your views are responsible for
        making the actual query and rendering the text response.  The response
        should be in the format:
            PRIMARY_KEY|TEXT_LABEL
        with one entry per line
    """
    if request.method != 'GET':
        raise Http404
    q_str, limit = request.GET.get('q', ''), request.GET.get('limit', None)
    excludes = request.GET.get('exclude','').split(',')
    if excludes:
        excludes = [int(e) for e in excludes if e]
    if (len(q_str) < 1) or (not limit):
        raise Http404
    return (q_str, excludes, limit)
    

class FbModelChoiceField(forms.CharField):
    """
    A model multiple choice field that uses a Facebook-like autocomplete
    interface / widget.
    
    This field is bound to the FbSelectMultiple Widget.
    
    If you use this outside of admin, you need to manually link to the
    javascript and css from FbSelectWidget
    
    Takes 6 additional named arguments:
    @multiple: select multiple objects at once? False by default
    @model: the model from which to select multiple
    @url: the widget makes a AJAX requests for autocompletion. this is the
        url that returns the autcomplete search results. the request is made
        to the url: url?q=query_string&limit=max_results
        the results should be returned as text, with one result on each
        line. each results should look like: primary_key|label
    @labeler: a function that takes a model object and returns a label.
        this is used for the initial labels.  default is just str(x)
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
        self.add_rel = kwargs.pop('add_rel', None)
        kwargs['widget'] = FbSelectWidget(
            url=kwargs.pop('url'), 
            model=self.model, 
            labeler=kwargs.pop('labeler', lambda x: str(x)),
            multiple=self.is_multiple, 
            no_duplicates=no_dupes,
            add_rel=self.add_rel
        )
        # if add_rel, use the related field widget wrapper for the add button
        if self.add_rel:
            kwargs['widget'] = admin.widgets.RelatedFieldWidgetWrapper(
                kwargs['widget'], self.add_rel, kwargs.pop('admin_site'))
        # just in case admin_site is still on there
        kwargs.pop('admin_site', None)
        s = super(FbModelChoiceField, self).__init__(*args, **kwargs)
        self.help_text = mark_safe("Start typing; we'll provide suggestions."
            + ("<br>%s" % self.help_text if self.help_text else ''))
        return s
    
    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError("This can't be left blank")
            return [] if self.is_multiple else None
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
        js = (static_content('scripts/framework/jquery-ui.packed.js'),
            static_content('scripts/admin/widgets/SearchModelChoiceWidget.js'))
        css = {'all': (static_content('css/framework/jquery.ui.css'),
            static_content('css/admin/SearchModelChoiceWidget.css'))}
    
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

class CKEditorWidget(forms.widgets.Textarea):
    """Widget that uses CKEditor with custom settings."""
    def render(self, name, value, attrs=None):
        return render_to_string("forms/ckeditor_widget.html", {'field':
            super(CKEditorWidget, self).render(name, value, attrs)})
    

class TinyMCEWidget(forms.widgets.Textarea):
    """
    Widget that uses TinyMCE editor with custom settings
    """
    def __init__(self, *args, **kwargs):
        csdict, csstring = kwargs.pop('custom_settings', None), ""
        try:
            for k, v in csdict.items():
                csstring = csstring + k + ':"' + v + '", \n'
            print csstring
        except:
            pass
        self.custom_settings = csstring
        return super(TinyMCEWidget, self).__init__(*args, **kwargs)

    class Media:
        pass

    def render(self, name, value, attrs=None):
        if value is not None:
            value = filter.escape(value)
        ta = super(TinyMCEWidget, self).render(name, value, attrs)
        custom_settings = mark_safe(self.custom_settings)
        return render_to_string("forms/tinymce_widget.html", locals())
    

class CropWidget(forms.widgets.HiddenInput):
    """Widget for CropField."""
    
    def __init__(self, *args, **kwargs):
        c = kwargs.pop('crop_size', None)
        self.crop_size = c
        self.display_size = kwargs.pop('display_size')
        self.aspect_ratio = float(c[0]) / float(c[1])
        self.image = None
        return super(CropWidget, self).__init__(*args, **kwargs)
    
    class Media:
        js = (static_content('scripts/framework/jquery.Jcrop.js'),)
        css = {'all': (static_content('css/framework/jquery.Jcrop.css'),)}
    
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