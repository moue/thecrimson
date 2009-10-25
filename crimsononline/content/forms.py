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
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Issue, Content, Section
from crimsononline.common.utils.misc import static_content


class AutoGenSlugWidget(forms.widgets.TextInput):
    """
    A slug widget that doesn't allow you to change pre-existing slugs.  
    Also automatically generates slugs based on some text field.
    @url => the url which responds with generated slug
    @date_field => css selector to gather issue date (sent with XHR)
    @text_field => css selector to gather text (sent with XHR)
    
    If you don't include a URL, then the autogeneration features just won't
    show up.
    """
    # todo: move the js out of the template and into class Media
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None)
        self.date_field = kwargs.pop('date_field', None)
        self.text_field = kwargs.pop('text_field', None)
        self.a, self.kw = args, kwargs
        
        # This is set in admin.ContentAdmin.get_form
        # Will be True if the article's been published, false otherwise
        self.editable = True
        
        super(AutoGenSlugWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs={}):
        input = super(AutoGenSlugWidget, self).render(name, value, attrs)
        if not self.editable:
            # render a disabled input, but we still need a hidden input to
            #  make sure the form validates (slugs are required)
            fakeinput = mark_safe(input.replace('id="id_slug"', 'disabled="1"'))
            input = mark_safe(input.replace('type="text"', 'type="hidden"'))
        date_field, text_field, url = self.date_field, self.text_field, self.url
        return render_to_string('forms/autogen_slug_widget.html', locals())
    

class MapBuilderWidget(forms.widgets.HiddenInput):
    
    class Media:
        js = (static_content('scripts/jquery.js'),
            static_content('scripts/jquery-ui-resizable.js'),
        )
    
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
        js = (static_content('scripts/framework/jquery-ui.packed.js'),
            static_content('scripts/admin/IssuePickerWidget.js'),)
        css = {'all': (static_content('css/framework/jquery.ui.css'),
            static_content('css/admin/IssuePickerWidget.css'),)}
    
    def __init__(self, *args, **kwargs):
        self.editable = True
        super(IssuePickerWidget, self).__init__(*args, **kwargs)
    
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
        is_editable = self.editable
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
        js = (static_content('scripts/framework/jquery-ui.packed.js'),
            static_content('scripts/admin/RelatedContentWidget.js'))
        css = {'all': (static_content('css/framework/jquery.ui.css'),
            static_content('css/admin/RelatedContent.css'))}
    
    def __init__(self, admin_site, *args, **kwargs):
        self.rel_types = kwargs.pop('rel_types', None)
        self.admin_site = admin_site
        self.c_types = []
        
        return super(RelatedContentWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        # set up content types
        print value
        if not self.c_types:
            for t in self.rel_types:
                if t not in self.admin_site._registry:
                    continue
                t_name = t._meta.object_name
                t_url = '../../../%s/%s/' % (t._meta.app_label, t_name.lower())
                t_id = ContentType.objects.get_for_model(t).pk
                self.c_types.append({'url': t_url, 'name': t_name, 'id': t_id})
        
        if value:
            if isinstance(value, basestring):
                value = [int(v) for v in value.split(';') if v]
            # grab all related content objects AND PRESERVE ORDER !!
            objs = []
            for v in value:
                objs.append(Content.objects.admin_objects().get(pk=v))
            
            # construct related content identifiers
            value = ['%d' % (o.pk) \
                for o in objs if o]
            value = ';'.join(value) + ';'
        else:
            # make sure value isn't '', [], or some other fail
            value = None
        
        hidden = super(RelatedContentWidget, self).render(name, value, attrs)
        # account for closeouts before midnight
        today, yesterday = datetime.now() + timedelta(days=1), datetime.now() + timedelta(days=-2)
        types = self.c_types
        return render_to_string("forms/related_content_widget.html", locals())
    


class RelatedContentField(forms.CharField):
    """The interface for adding / editing related content."""
    
    def __init__(self, *args, **kwargs):
        
        kwargs['widget'] = RelatedContentWidget(
            rel_types=kwargs.pop('rel_types', []),
            admin_site=kwargs.pop('admin_site')
        )
        return super(RelatedContentField, self).__init__(*args, **kwargs)
    
    def clean(self, value):
        """Turns value into a list of Content objects
        
        value is received as a ; delimited set of primary keys
        """

        if not value:
            return []
        ids = [int(id) for id in value.split(';') if id]
        q = reduce(lambda x, y: x | y, [Q(pk=p) for p in ids])
        objs = list(Content.objects.admin_objects().filter(q))
        # retrieving Content objs MUST preserve their order!!!
        objs = dict([(obj.pk, obj) for obj in objs])
        return [objs[pk] for pk in ids]
    
