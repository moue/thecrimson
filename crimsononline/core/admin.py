from datetime import datetime, timedelta
from django import forms
from django.conf import settings
from django.contrib import admin
from django.forms import ModelForm
from django.contrib.auth.models import User
from crimsononline.core.models import *

"""
class ContributorForm(ModelForm):
    boards = forms.fields.MultipleChoiceField(
        required=False, 
        choices=(
            ('Arts Board', 'Arts',),
            ('Biz Board', 'Biz',),
            ('Design Board','Design',),
            ('Ed Board','Ed',),
            ('FM Board','FM',),
            ('IT Board','IT',),
            ('News Board','News',),
            ('Photo Board', 'Photo',),
            ('Sports Board','Sports'),
        )
    )
    class Meta:
        model = Contributor
        
    def save(self, commit=True):
        if boards != []
            
        return super(ContributorForm, self).save(commit)
"""

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

class ImageInline(admin.TabularInline):
    model = Image

class ImageGalleryAdmin(admin.ModelAdmin):
    pass
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