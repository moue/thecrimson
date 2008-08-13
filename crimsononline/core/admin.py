from datetime import datetime, timedelta
from django import forms
from django.conf import settings
from django.contrib import admin
from django.forms import ModelForm
from django.forms.util import ErrorList
from django.forms.models import ModelChoiceIterator
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from crimsononline.core.models import *

class ContributorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'middle_initial',)
    search_fields = ('first_name', 'last_name',)
    fieldsets = (
        (None, {
            'fields': (
                ('first_name', 'middle_initial', 'last_name'),
                'type',
                'is_active',
            )
        }),
        ('Crimson Staff Settings', {
            'description': '<b>Leave this section blank if this contributor is not on the staff of the Crimson!</b>',
            'classes': ('collapse',),
            'fields': (
                'boards',
                ('email', 'phone',), 
                ('board_number', 'class_of',),
            )
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # create a user if one does not exist
        # then set the groups of the user
        boards = form.cleaned_data['boards']
        print obj
        print obj.user
        print boards
        if obj.user is None and boards != []:
            u = User()
            class_of = form.cleaned_data['class_of']
            if class_of is None:
                class_of = 0
            u.username = ('%s_%s_%s_%d' % (
                form.cleaned_data['first_name'],
                form.cleaned_data['middle_initial'],
                form.cleaned_data['last_name'],
                class_of
            ))[:30]
            u.set_unusable_password() # auth is done with Harv PIN
            u.is_staff = True
            u.save()
            obj.user = u
        if obj.user != None:
            groups = [board.group for board in boards]
            obj.user.groups = groups
            obj.user.save()
        return super(ContributorAdmin, self).save_model(request, obj, form, change)
    

admin.site.register(Contributor, ContributorAdmin)

class IssueAdmin(admin.ModelAdmin):
    list_display = ('issue_date',)
    search_fields = ('issue_date',)
    fields = ('issue_date', 'web_publish_date', 'comments', 'web_only',)

admin.site.register(Issue, IssueAdmin)


class TagAdmin(admin.ModelAdmin):
    list_display = ('text',)
    search_fields = ('text',)
    fields = ('text',)

admin.site.register(Tag, TagAdmin)


admin.site.register(Image)

class ImageSelectMultipleWidget(forms.widgets.SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        output = '<div id="form-image-chooser"></div>\n'
        output += super(ImageSelectMultipleWidget, self). \
            render(name, value, attrs, choices)
        return mark_safe(output)

class ImageGalleryForm(ModelForm):
    # we use a special widget here so that we can inject an extra div
    #    above the select multiple field.  the extra div is where
    #    the javascript inserts img previews for img selection.
    images = forms.ModelMultipleChoiceField(
        Image.objects.none(),
        widget=ImageSelectMultipleWidget()
    )
    
    class Meta:
        model = ImageGallery
    
    class Media:
        css = {
            'all': ('css/ImageGalleryAjax.css',)
        }
        js = ('js/ImageGalleryAjax.js',)

class ImageGalleryAdmin(admin.ModelAdmin):
    fields = ('images', 'cover_image', 'tags')
    filter_horizontal = ('tags',)
    form = ImageGalleryForm
    
    # we need to set the list of images (that show up) on a per instance basis
    # unbound forms => no images
    # bound forms => images belonging to the ImageGallery instance
    def get_form(self, request, obj=None):
        f = super(ImageGalleryAdmin,self).get_form(request, obj)
        
        # no bound => no images
        qs = Image.objects.none()
        
        # yes bound => images that belong to the current ImageGallery
        if obj is not None:
            for img in obj.images.all()[:]:
                qs = qs | Image.objects.filter(pk=img.pk)
        
        # querysets are set for bound and unbound forms because if
        #    we don't set the queryset on unbound forms, loading a bound
        #    form and then loading an unbound form leads to the wrong
        #    images showing up.  (maybe querysets are cached improperly?)
        f.images.queryset = qs
        return f

admin.site.register(ImageGallery, ImageGalleryAdmin)

class ArticleForm(ModelForm):
    teaser = forms.fields.CharField(
        widget=forms.TextInput(attrs={'size':'70'}),
        required=False
    )
    subheadline = forms.fields.CharField(
        widget=forms.TextInput(attrs={'size':'70'}),
        required=False
    )
    headline = forms.fields.CharField(
        widget=forms.TextInput(attrs={'size':'70'})
    )
    text = forms.fields.CharField(
        widget=forms.Textarea(attrs={'rows':'50', 'cols':'67'})
    )
    
    class Meta:
        model = Article

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('headline', 'section', 'issue',)
    search_fields = ('headline', 'text',)
    filter_horizontal = ('contributors', 'tags',)
    form = ArticleForm
    
    def has_change_permission(self, request, obj=None):
        u = request.user
        if u.is_superuser:
            return True
        # cannot make changes after 60 minutes from uploaded time
        elif obj and not u.has_perm('core.article.can_change_after_timeout'):
            return (datetime.now() - obj.uploaded_on).seconds < (60 * 60)
        return super(ArticleAdmin, self).has_change_permission(request, obj)
    
    def queryset(self, request):
        u = request.user
        qs = super(ArticleAdmin,self).queryset(request)
        if u.is_superuser:
            return qs
       
        # restrict editing of articles uploaded before 60 min ago
        if not u.has_perm('core.article.can_change_after_timeout'):
            t = datetime.now() - timedelta(seconds=(60*60))
            qs = qs.filter(uploaded_on__gt=t)
            u.message_set.create(message='Note: you can only change articles uploaded in the last hour.')
        return qs
    
admin.site.register(Article, ArticleAdmin)