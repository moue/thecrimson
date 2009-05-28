"""
Forms, widgets, fields.
However, put forms specifically for Admin in admin.py, not here
"""

from datetime import date, datetime, timedelta
from time import strptime
from re import compile
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Issue, ContentGeneric

class AutoGenSlugWidget(forms.widgets.TextInput):
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        self.date_field = kwargs.pop('date_field')
        self.text_field = kwargs.pop('text_field')
        super(AutoGenSlugWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs={}):
        if value: attrs['disabled'] = 1
        input = super(AutoGenSlugWidget, self).render(name, value, attrs)
        date_field, text_field, url = self.date_field, self.text_field, self.url
        return render_to_string('forms/autogen_slug_widget.html', locals())
    

class MapBuilderWidget(forms.widgets.HiddenInput):
    def render(self, name, value, attrs=None):
        return render_to_string("forms/map_builder_widget.html", locals())
    

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
        js = ('/site_media/scripts/framework/jquery-ui.packed.js',
            '/site_media/scripts/admin/IssuePickerWidget.js',)
        css = {'all': ('/site_media/css/framework/jquery.ui.css',
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
            value = issue_date.strftime(r"%m/%d/%Y")
        year = datetime.now().year
        special_choices = render_to_string("ajax/special_issues_fragment.html", 
            {'issues': Issue.objects.special.filter(issue_date__year=year), 
            'blank': "----", 'choice': value}
        )
        hidden = super(IssuePickerWidget, self).render(name, value, attrs)
        return render_to_string("forms/issue_picker_widget.html", locals())
    


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


class RelatedContentWidget(forms.widgets.HiddenInput):
    class Media:
        js = ('/site_media/scripts/framework/jquery-ui.packed.js',
            '/site_media/scripts/admin/RelatedContentWidget.js',)
        css = {'all': ('/site_media/css/framework/jquery.ui.css',
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
        return render_to_string("forms/related_content_widget.html", locals())
    


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