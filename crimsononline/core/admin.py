from datetime import datetime, timedelta
from re import compile
from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from crimsononline.core.models import *

class TagForm(forms.ModelForm):
    ALLOWED_REGEXP = compile(r'[A-Za-z\s]+$')
    class Meta:
        model = Tag
    def clean_text(self):
        text = self.cleaned_data['text']
        print text
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
    def clean_huid_hash(self):
        if len(self.cleaned_data['huid_hash']) != 8:
            raise forms.ValidationError('HUID must be 8 digits long')
        return self.cleaned_data['huid_hash']

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
            'description': '<h3><b>Leave this section blank if this contributor ' \
                            'is not on the staff of The Crimson!</b></h3>',
            'classes': ('collapse',),
            'fields': (
                'boards',
                ('email', 'phone',), 
                ('board_number', 'class_of',),
                'huid_hash',
            )
        }),
    )
    form = ContributorForm
    
    def save_model(self, request, obj, form, change):
        # create a user if one does not exist
        # then set the groups of the user
        boards = form.cleaned_data['boards']
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
        return super(ContributorAdmin, self).save_model(
            request, obj, form, change)
    

admin.site.register(Contributor, ContributorAdmin)

class IssueAdmin(admin.ModelAdmin):
    list_display = ('issue_date',)
    search_fields = ('issue_date',)
    fields = ('issue_date', 'web_publish_date', 'comments',)

admin.site.register(Issue, IssueAdmin)

class ImageAdmin(admin.ModelAdmin):
    fields = ('pic', 'caption', 'kicker', 'contributor', 'tags',)
    filter_horizontal = ('tags',)
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
    # super's clean thinks that valid Images are images in the initial queryset
    #    but that is not the case; all images are valid.  we temporarily change
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

class ImageGalleryForm(ModelForm):
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
    filter_horizontal = ('tags',)
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


class ImageGallerySelectWidget(forms.widgets.HiddenInput):
    def render(self, name, value, attrs=None, choices=()):
        if value:
            # HACK: we shouldn't have to re-get the image gallery
            ig = ImageGallery.objects.get(pk=value)
            _html = '<ul class="current_gallery">'
            
            from crimsononline.templ.templatetags.crimson_filters import to_thumb_tag
            _html += ''.join(['<li>%s</li>' % to_thumb_tag(img) for img in ig.images.all()])
            _html += '<ul>'
            #thumbs_html = thumbs_html % _html
        else:
            #thumbs_html = thumbs_html % ''
            _html = ''
        # show thumbnails of all the galleries
        slct = 'selected="selected"'
        thumbs_html = """<div class="image_gallery_select">%s
        <div class="image_gallery_search">
            Tag: <input id="search_by_tag"></input> | 
            Start Month: <select id="search_by_start_year">%s</select>
            <select id="search_by_start_month">%s</select> |
            End Month: <select id="search_by_end_year">%s</select>
            <select id="search_by_end_month">%s</select>
            <a href="#" class="button" id="find_image_gallery_button">Find</a>
        </div><div class="image_gallery_results"></div></div>""" % (_html,
            ''.join(['<option value="%d"%s>%d</option>' % (i, slct if i == datetime.now().year else '', i) for i in range(1996, datetime.now().year + 1)]), 
            ''.join(['<option value="%d"%s>%d</option>' % (i, slct if i == datetime.now().month else '', i) for i in range(1, 13)]),
            ''.join(['<option value="%d"%s>%d</option>' % (i, slct if i == datetime.now().year else '', i) for i in range(1996, datetime.now().year + 1)]),
            ''.join(['<option value="%d"%s>%d</option>' % (i, slct if i == datetime.now().month else '', i) for i in range(1, 13)]),
            )
        return mark_safe(super(ImageGallerySelectWidget, self).render(
            name, value, attrs) + thumbs_html)
        

class ImageGalleryChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(ImageGalleryChoiceField,self).__init__(*args, **kwargs)
        self.widget = admin.widgets.RelatedFieldWidgetWrapper(
            self.widget,
            Article._meta.get_field('image_gallery').rel,
            admin.site
        )
        
class SingleImageChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(SingleImageChoiceField, self).__init__(*args, **kwargs)
        self.widget = admin.widgets.RelatedFieldWidgetWrapper(
            self.widget, 
            ImageGallery._meta.get_field('images').rel, 
            admin.site
        )

class ArticleForm(ModelForm):
    #TODO: insert logic to display current image gallery in the image section
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
    image_gallery = ImageGalleryChoiceField(ImageGallery.objects.all(), 
        widget=ImageGallerySelectWidget(), required=False)
    single_image = SingleImageChoiceField(Image.objects.all(), required=False)
    
    class Meta:
        model = Article

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('headline', 'section', 'issue',)
    search_fields = ('headline', 'text',)
    filter_horizontal = ('contributors', 'tags',)
    exclude = ['is_published']
    fieldsets = (
        ('Headline', {
            'fields': ('headline', 'subheadline', 'slug',),
        }),
        ('Text', {
            'fields': ('text',)
        }),
        ('Byline', {
            'fields': ('contributors', 'byline_type',)
        }),
        ('Print', {
            'fields': ('issue', 'section', 'page',)
        }),
        ('Web', {
            'fields': ('priority', 'web_only', 'tags',)
        }),
        ('Editing', {
            'fields': ('proofer', 'sne',)
        }),
        ('Image(s)', {
            'classes': ('collapse',),
            'fields': ('image_gallery', 'single_image',)
        })
    )
    form = ArticleForm
    
    class Media:
        js = (
            'scripts/jquery.js',
            'scripts/admin/Article.js',
			'scripts/framework/jquery.sprintf.js',
        )
    
    """
    # we need to set the list of images (that show up) on a per instance basis
    # unbound forms => no images
    # bound forms => images belonging to the ImageGallery instance
    def get_form(self, request, obj=None):
        f = super(ArticleAdmin,self).get_form(request, obj)
        
        # no bound => no images
        qs = ImageGallery.objects.none()
        
        # yes bound => images that belong to the current ImageGallery
        if obj is not None:
            if obj.image_gallery is not None:
                qs = ImageGallery.objects.filter(pk=obj.image_gallery.pk)
        
        # querysets are set for bound and unbound forms because if
        #    we don't set the queryset on unbound forms, loading a bound
        #    form and then loading an unbound form leads to the wrong
        #    images showing up.  (maybe querysets are cached improperly?)
        f.base_fields['image_gallery'].queryset = qs
        return f
    """
    
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
            u.message_set.create(message='Note: you can only change articles' \
                                            ' uploaded in the last hour.')
        return qs
        
    def save_model(self, request, obj, form, change):
        img = form.cleaned_data['single_image']
        # turn the image into a gallery, attach the gallery to the article
        if img:
            gal = ImageGallery.objects.create(
                title=img.caption, description=img.kicker, cover_image=img)
            gal.images = [img]
            gal.save()
            obj.image_gallery = gal
        return super(ArticleAdmin, self).save_model(request, obj, form, change)

admin.site.register(Article, ArticleAdmin)