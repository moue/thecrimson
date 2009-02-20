from datetime import datetime, timedelta
from re import compile
from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.hashcompat import md5_constructor
from django.template.defaultfilters import truncatewords
from crimsononline.core.models import *
from crimsononline.admin_cust import forms as cforms
from crimsononline.admin_cust.forms import FbModelChoiceField, IssuePickerField, MapBuilderField, RelatedContentField, CropField


class ContentGenericModelForm(ModelForm):
    """
    Parent class for ContentGeneric model forms.
    Doesn't actually work by itself.
    """
    tags = forms.ModelMultipleChoiceField(Tag.objects.all(), required=True,
        widget=admin.widgets.RelatedFieldWidgetWrapper(
            admin.widgets.FilteredSelectMultiple('Tags', False),
            ContentGeneric._meta.get_field('tags').rel,
            admin.site
        )
    )
    contributors = FbModelChoiceField(required=True, multiple=True,
        url='/admin/core/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        add_rel=ContentGeneric._meta.get_field('contributors').rel
    )
    issue = IssuePickerField(label='Issue Date', required=True)
    section = forms.ModelChoiceField(Section.all(), required=True)
    priority = forms.IntegerField(required=False, initial=0,
        help_text='Higher priority articles are displayed first.' \
        'Priority be positive or negative.')
    
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        # since tags and contributor aren't normal Django fields, admin
        #  won't load their values by default. override that behavior
        #  by sticking the values into the 'initial' arg
        if instance:
            initial = {
                'tags': [t.pk for t in instance.tags.all()],
                'contributors': [c.pk for c in instance.contributors.all()],
                'issue': instance.issue.pk,
                'section': instance.section.pk,
                'priority': instance.priority,
            }
            if not kwargs.get('initial', None):
                kwargs['initial'] = {}
            kwargs['initial'].update(initial)
        return super(ContentGenericModelForm, self).__init__(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        obj = super(ContentGenericModelForm, self).save(*args, **kwargs)
        obj.save()
        obj.tags = self.cleaned_data['tags']
        obj.contributors = self.cleaned_data['contributors']
        obj.section = self.cleaned_data['section']
        obj.issue = self.cleaned_data['issue']
        obj.priority = self.cleaned_data['priority']
        return obj
        

class TagForm(forms.ModelForm):
    ALLOWED_REGEXP = compile(r'[A-Za-z\s]+$')
    class Meta:
        model = Tag
    def clean_text(self):
        text = self.cleaned_data['text']
        if not TagForm.ALLOWED_REGEXP.match(text):
            raise forms.ValidationError(
                'Tags can only contain letters and spaces')
        return text.lower()

class TagAdmin(admin.ModelAdmin):
    form = TagForm

admin.site.register(Tag, TagAdmin)


class ContributorForm(forms.ModelForm):
    class Meta:
        model = Contributor
    huid = forms.fields.CharField(label='HUID')
    # HOW DO I MAKE THIS ACTUALLY DISPLAY 'HUID' INSTEAD OF 'Huid'
    def clean_huid_hash(self):
        h = self.cleaned_data['huid_hash']
        if h and len(h) != 8:
            raise forms.ValidationError('HUID must be 8 digits long')
        return self.cleaned_data['huid_hash']

class ContributorSelfAdmin(admin.ModelAdmin):
    fields = ('profile_text', 'profile_pic', 'email', 'phone')
    form = ContributorForm
    
class ContributorAdmin(admin.ModelAdmin):
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
            'description': """<h3><b>Leave this section blank if this contributor 
                            is not on the staff of The Crimson!</b></h3>""",
            'classes': ('collapse',),
            'fields': (
                'boards',
                ('email', 'phone',), 
                ('board_number', 'class_of',),
                'huid',
                ('profile_text', 'profile_pic'),
            )
        }),
    )
    form = ContributorForm
    
    def save_model(self, request, obj, form, change):
        # create a user if one does not exist
        # then set the groups of the user
        boards = form.cleaned_data['boards']
        huid_hash = md5_constructor(form.cleaned_data['huid']).hexdigest()
        if obj.user is None and boards != []:
            u = User()
            u.save()
            ud = UserData(user=u)
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
            ud.save()
            obj.user = u
        if obj.user != None:
            groups = [board.group for board in boards]
            obj.user.groups = groups
            obj.user.save()
            ud = obj.user.get_profile()
            ud.huid_hash = huid_hash
            ud.save()
        return super(ContributorAdmin, self).save_model(
            request, obj, form, change)
    

admin.site.register(Contributor, ContributorAdmin)

class IssueAdmin(admin.ModelAdmin):
    list_display = ('issue_date',)
    search_fields = ('issue_date',)
    fields = ('issue_date', 'web_publish_date', 'special_issue_name', 'comments',)

admin.site.register(Issue, IssueAdmin)

class ImageAdminForm(ContentGenericModelForm):
    class Meta:
        model = Image
    
	# the different sizes to crop. these should all be square sizes
	CROP_SIZES = (Image.SIZE_THUMB, )
	
    caption = forms.fields.CharField(
        widget=forms.Textarea(attrs={'rows':'5', 'cols':'40'}),
        required=True)
    thumbnail = CropField(required=False, crop_size=Image.SIZE_THUMB,
        display_size=Image.SIZE_STAND)
    
    def save(self, *args, **kwargs):
        i = super(ImageAdminForm, self).save(*args, **kwargs)
        # logic for saving the cropped stuffs
        data = self.cleaned_data['thumbnail']
        if data:
            hori_ratio = float(i.pic.width) / float(Image.SIZE_STAND[0]) 
            vert_ratio = float(i.pic.height) / float(Image.SIZE_STAND[1])
            # ratio the image is actually scaled at
            scale_ratio = max(hori_ratio, vert_ratio)
            # if this ratio is < 1, then the image wasn't scaled at all
            if scale_ratio < 1.0:
                scale_ratio = 1
            data = map(lambda x: int(x * scale_ratio), data)
            i.crop(Image.SIZE_THUMB[0], Image.SIZE_THUMB[1], *data)
        return i

class ImageAdmin(admin.ModelAdmin):
    fields = ('pic', 'thumbnail', 'caption', 'kicker', 'section', 'issue',
        'priority', 'contributors', 'tags')
    form = ImageAdminForm
    class Media:
        js = (
            'scripts/jquery.js',
        )
    def get_form(self, request, obj=None):
        f = super(ImageAdmin, self).get_form(request, obj)
        f.base_fields['thumbnail'].widget.image = obj	
        return f
        
admin.site.register(Image, ImageAdmin)


class ImageSelectMultipleWidget(forms.widgets.SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        output = '<div id="images-bank"><ul class="image-list"></ul>' \
                    '<div class="links"></div></div>\n'
        output += super(ImageSelectMultipleWidget, self). \
            render(name, value, attrs, choices)
        output += '<div id="images-current"><h3>Images in this ' \
                    'Image Gallery</h3><ul class="image-list"></ul></div>'
        return mark_safe(output)

class ImageSelectModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    # super's clean thinks that valid Images = images in the initial queryset
    #    but that's not the case; all images are valid.  we temporarily change
    #    the queryset, do a clean, and then change the queryset back (to
    #    mitigate side effects).
    def clean(self, value):
        qs = self.queryset
        self.queryset = Image.objects
        c = super(ImageSelectModelMultipleChoiceField, self).clean(value)
        self.queryset = qs
        return c
    

class ImageSelectModelChoiceField(forms.ModelChoiceField):
    # see above
    def clean(self, value):
        qs = self.queryset
        self.queryset = Image.objects
        c = super(ImageSelectModelChoiceField, self).clean(value)
        self.queryset = qs
        return c

class ImageGalleryForm(ContentGenericModelForm):
    # we use a special widget here so that we can inject an extra div
    #    above the select multiple field.  the extra div is where
    #    the javascript inserts img previews for img selection.
    images = ImageSelectModelMultipleChoiceField(
        Image.objects.none(),
        widget=ImageSelectMultipleWidget(),
    )
    cover_image = ImageSelectModelChoiceField(
        Image.objects.none(),
    )
    
    class Meta:
        model = ImageGallery
    
    class Media:
        css = {
            'all': ('css/admin/ImageGallery.css',)
        }
        js = (
            'scripts/jquery.js',
            'scripts/admin/ImageGallery.js', 
        )
    

class ImageGalleryAdmin(admin.ModelAdmin):
    fields = ('title', 'description', 'images', 'cover_image', 'tags')
    form = ImageGalleryForm
    
    # we need to set the list of images (that show up) on a per instance basis
    # unbound forms => no images
    # bound forms => images belonging to the ImageGallery instance
    def get_form(self, request, obj=None):
        f = super(ImageGalleryAdmin,self).get_form(request, obj)
        
        # no bound => no images
        qs = Image.objects.none()
        cover_qs = Image.objects.none()
        
        # yes bound => images that belong to the current ImageGallery
        if obj is not None:
            for img in obj.images.all()[:]:
                qs = qs | Image.objects.filter(pk=img.pk)
            cover_qs = Image.objects.filter(pk=obj.cover_image.pk)
        
        # querysets are set for bound and unbound forms because if
        #    we don't set the queryset on unbound forms, loading a bound
        #    form and then loading an unbound form leads to the wrong
        #    images showing up.  (maybe querysets are cached improperly?)
        f.base_fields['images'].queryset = qs
        f.base_fields['cover_image'].queryset = cover_qs
        return f

admin.site.register(ImageGallery, ImageGalleryAdmin)


class ArticleForm(ContentGenericModelForm):
    teaser = forms.fields.CharField(
        widget=forms.Textarea(attrs={'rows':'5', 'cols':'67'}),
        required=False, help_text="""
        A short sample from the article, or a summary of the article.<br>
        If you don't provide a teaser, we will automatically generate one for you.
        """
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
    contributors = FbModelChoiceField(required=True, multiple=True,
        url='/admin/core/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        #add_rel=Article._meta.get_field('contributors').rel)
        )
    proofer = FbModelChoiceField(required=True, multiple=False,
        url='/admin/core/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    sne = FbModelChoiceField(required=True, multiple=False,
        url='/admin/core/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    rel_content = RelatedContentField(label='New Content', required=False, admin_site=admin.site, rel_types=[Image, ImageGallery, Article])
    
    def clean_teaser(self):
        """Adds a teaser if one does not exist."""
        if self.cleaned_data['teaser']:
            return self.cleaned_data['teaser']
        return truncatewords(self.cleaned_data['text'], 20)
    
    def save(self, *args, **kwargs):
        rel = self.cleaned_data.pop('rel_content', [])
        obj = super(ArticleForm, self).save(*args, **kwargs)
        obj.rel_content.clear()
        for i, r in enumerate(rel):
            x = ArticleContentRelation(order=i, article=obj, related_content=r)
            x.save()
        return obj
    
    class Meta:
        model = Article

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('headline', 'section', 'issue',)
    search_fields = ('headline', 'text',)
    exclude = ['is_published']
    fieldsets = (
        ('Headline', {
            'fields': ('headline', 'subheadline', 'slug',),
        }),
        ('Text', {
            'fields': ('text', 'teaser',),
        }),
        ('Byline', {
            'fields': ('contributors', 'byline_type',),
        }),
        ('Print', {
            'fields': ('issue', 'section', 'page',),
        }),
        ('Web', {
            'fields': ('priority', 'web_only', 'tags',),
        }),
        ('Editing', {
            'fields': ('proofer', 'sne',),
        }),
        ('Associated Content', {
            'fields': ('rel_content',),
        }),
        #('Map(s)', {
        #    'classes': ('collapse',),
        #    'fields': ('maps',),
        #})
    )
    form = ArticleForm
    
    class Media:
        js = (
            'scripts/jquery.js',
            'scripts/admin/Article.js',
            'scripts/framework/jquery.sprintf.js',
        )
        css = {
            'all': ('css/admin/Article.css',)
        }
    
    #def save_model(self, request, obj, form, change):
    #    obj.save()
    #    obj.rel_content.clear()
    #    for i, r in enumerate(form.cleaned_data['rel_content']):
    #        x = ArticleContentRelation(order=i, article=obj, related_content=r)
    #        x.save()
    
    def has_change_permission(self, request, obj=None):
        u = request.user
        if u.is_superuser:
            return True
        # cannot make changes after 60 minutes from uploaded time
        elif obj and not u.has_perm('core.article.can_change_after_timeout'):
            return (datetime.now() - obj.created_on).seconds < (60 * 60)
        return super(ArticleAdmin, self).has_change_permission(request, obj)
    
    def queryset(self, request):
        u = request.user
        qs = super(ArticleAdmin,self).queryset(request)
        if u.is_superuser:
            return qs
       
        # restrict editing of articles uploaded before 60 min ago
        if not u.has_perm('core.article.can_change_after_timeout'):
            t = datetime.now() - timedelta(seconds=(60*60))
            qs = qs.filter(created_on__gt=t)
            u.message_set.create(message='Note: you can only change articles' \
                                            ' uploaded in the last hour.')
        return qs
    

admin.site.register(Article, ArticleAdmin)


class MarkerInline(admin.TabularInline):
    model = Marker
    extra = 10
    fields = ('popup_text','lat','lng')

class MapForm(ModelForm):
    map_preview = MapBuilderField(label='Map Preview', required=False)
    
    def __init__(self, *args, **kwargs):
        s = super(MapForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Map

class MapAdmin(admin.ModelAdmin):
    
    search_fields = ('title','caption',)
    form = MapForm
    
    inlines = [
        MarkerInline,
    ]

    fieldsets = (
        ('Map Setup', {
            'fields': ('title', 'caption','map_preview'),
        }),
        ('Details', {
            'classes': ('frozen','collapse'),
            'fields': ('zoom_level','center_lng','center_lat','display_mode','width','height',),
        }))

        
admin.site.register(Map, MapAdmin)
admin.site.register(Marker)