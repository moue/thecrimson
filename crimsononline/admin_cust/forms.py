from datetime import date, datetime, timedelta
from time import strptime
from re import compile

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from crimsononline.core.models import Issue, ContentGeneric


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
        return render_to_string("widgets/crop_widget.html", locals())
    
    

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
        return tuple(map(lambda x: int(x), value.split(',')))
    


class MapBuilderWidget(forms.widgets.HiddenInput):
    def render(self, name, value, attrs=None):
        return render_to_string("widgets/map_builder.html", locals())
    


class MapBuilderField(forms.CharField):
    """
    A field that allows you to add a map via a map builder.
    
    Always uses the MapBuilderWidget.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = MapBuilderWidget()
        return super(MapBuilderField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError("This can't be left blank")
            return
        return
    


class IssuePickerWidget(forms.widgets.HiddenInput):
    """
    Widget that uses a calendar picker and ajax to pick issues.
    """
    
    class Media:
        js = ('/site_media/scripts/framework/jquery.ui.datepicker.js',
                '/site_media/scripts/admin/IssuePickerWidget.js',)
        css = {'all': ('/site_media/css/framework/jquery.ui.datepicker.css',
                        '/site_media/css/admin/IssuePickerWidget.css',),}
    
    def render(self, name, value, attrs=None):
        meta_select = "daily"
        if value:
            # this assumes that there are no errors (the field gets cleaned correctly)
            #  if there's an error that needs to be corrected on the form, then 
            #  the next line won't work, since value will be a date string
            try:
                issue = Issue.objects.get(pk=int(value))
                issue_date = issue.issue_date
                if issue.special_issue_name:
                    meta_select = "special"
            except ValueError:
                dt = strptime(value, r"%m/%d/%Y")
                issue_date = date(dt[0], dt[1], dt[2])
        else:
            # default value is the next issue
            issue_date = datetime.now()
            if issue_date.hour > 11:
                issue_date = issue_date.date() + timedelta(days=1)
            else:
                issue_date = issue_date.date()
            try:
                issue = Issue.objects.get(issue_date=issue_date)
                value = issue.pk
            except:
                issue = None
        year = datetime.now().year
        special_choices = render_to_string("special_issues_fragment.html", 
            {'issues': Issue.objects.special.filter(issue_date__year=year), 
            'blank': "----", 'choice': value}
        )
        hidden = super(IssuePickerWidget, self).render(name, value, attrs)
        return render_to_string("widgets/issue_picker.html", locals())
    


class IssuePickerField(forms.CharField):
    """
    A field that allows you to pick an issue via a date picker.
    
    Always uses the IssuePickerWidget.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = IssuePickerWidget()
        return super(IssuePickerField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError("This can't be left blank")
            return
        # if the value is in dd/mm/yyyy format, look for / create an issue
        DATE_FMT = compile(r'\d{2}/\d{2}/\d{4}')
        if DATE_FMT.match(value):
            dt = strptime(value, r"%m/%d/%Y")
            dt = date(dt[0], dt[1], dt[2])
            try:
                issue = Issue.objects.daily.get(issue_date=dt)
            except ObjectDoesNotExist:
                issue = Issue(issue_date=dt)
                issue.save()
            return issue
        # otherwise, grab the (special) issue from db
        else:
            try:
                return Issue.objects.get(pk=int(value))
            except: # the frontend should ensure that these errors never happen
                raise forms.ValidationError("Something terrible happened!")
    


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
        # in case its a string?
        if value and value.__class__ == unicode:
            value = list(map(lambda x: int(x), value.split(',')))
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
        url, is_multiple, no_dupes = self.url, self.is_multiple, self.no_duplicates
        return render_to_string("widgets/fb_select_multiple.html", locals())
    


class FbModelChoiceField(forms.CharField):
    """
    A model multiple choice field that uses a Facebook-like autocomplete
    interface / widget.
    
    This field is bound to the FbSelectMultiple Widget.
    
    Takes 6 additional named arguments:
    multiple: select multiple objects at once? False by default
    model: the model from which to select multiple
    url: the widget makes a AJAX requests for autocompletion. this is the
        url that returns the autcomplete search results. the request is made
        to the url: url?q=query_string&limit=max_results
        the results should be returned as text, with one result on each
        line. each results should look like: primary_key|label
    labeler: a function that takes a model object and returns a label.
        this is used for the initial labels.
    no_duplicates: is true, AJAX query will tack on the parameter
        exclude, with value a list of values to exclude in the autosuggest.
        eg: url?q=fasman&limit=10&exclude=4,1,2
    add_rel: the relation object? required for the "add related" button.
        None by default. If you set this, you also need to set admin_site.
    admin_site: the admin site instance.  Not required.  None by default.
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
        self.help_text = "Start typing; we'll provide suggestions.<br>%s" % self.help_text
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
    


class RelatedContentWidget(forms.widgets.HiddenInput):
    class Media:
        js = ('/site_media/scripts/framework/jquery-ui.packed.js',
            '/site_media/scripts/admin/RelatedContentWidget.js',)
        css = {'all': ('/site_media/css/framework/jquery.ui.datepicker.css',
            '/site_media/css/admin/RelatedContent.css'),}
    
    def __init__(self, admin_site, *args, **kwargs):
        self.rel_types = kwargs.pop('rel_types', None)
        self.admin_site = admin_site
        self.c_types = []
        
        return super(RelatedContentWidget, self).__init__(*args, **kwargs)
        
    def render(self, name, value, attrs=None):
        if not self.c_types:
            for t in self.rel_types:
                if t not in self.admin_site._registry:
                    continue
                t_name = t._meta.object_name
                t_url = '../../../%s/%s/' % (t._meta.app_label, t_name.lower())
                t_id = ContentType.objects.get_for_model(t).pk
                self.c_types.append({'url': t_url, 'name': t_name, 'id': t_id})
        
        if value:
            # grab all related content objects AND PRESERVE ORDER !!
            objs = []
            for v in value:
                objs.append(ContentGeneric.objects.get(pk=v))
            
            # this doesn't preserve order
            #query = reduce(lambda x, y: x|y, [Q(pk=v) for v in value])
            #objs = ContentGeneric.objects.filter(query)
            
            # construct related content identifiers
            value = ['%d,%d' % (o.content_type.pk, o.object_id) \
                for o in objs if o]
            value = ';'.join(value) + ';'
        else:
            # make sure value isn't '', [], or some other fail
            value = None
        hidden = super(RelatedContentWidget, self).render(name, value, attrs)
        today, yesterday = datetime.now(), datetime.now() + timedelta(days=-2)
        types = self.c_types
        return render_to_string("widgets/related_content.html", locals())
    


class RelatedContentField(forms.CharField):
    """
    The interface for adding / editing related content.
    """
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = RelatedContentWidget(
            rel_types=kwargs.pop('rel_types', []),
            admin_site=kwargs.pop('admin_site')
        )
        return super(RelatedContentField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        """
        Turns value into a list of ContentGeneric objects
        value is received as a ; delimited set of , delimited pairs
        """
        if not value:
            return []
        
        ids = [tuple(v.split(',')) for v in value.split(';') if v]
        
        # retrieving ContentGeneric objs MUST preserve their order!!!
        objs = []
        for p in ids:
            objs.append(ContentGeneric.objects.get(
                content_type__pk=p[0], object_id=p[1]))
         
        # this is faster? but doesn't work because it doesn't preserve order       
        #q = [Q(content_type__pk=p[0], object_id=p[1]) for p in ids]
        #q = reduce(lambda x, y: x | y, q)
        #objs = list(ContentGeneric.objects.filter(q))
        
        if len(objs) != len(ids):
            raise Exception('Unexpected ContentGeneric identifiers.')
        return objs
    

