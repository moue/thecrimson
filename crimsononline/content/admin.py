from datetime import datetime, timedelta, date
from re import compile
from time import strptime
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.conf.urls.defaults import patterns
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import ModelForm
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.defaultfilters import truncatewords
from django.utils import simplejson, html
from django.utils.safestring import mark_safe
from django.utils.hashcompat import md5_constructor
from crimsononline.content.models import *
from crimsononline.content.forms import *
from crimsononline.common.utils.strings import alphanum_only
from crimsononline.common.forms import \
    FbModelChoiceField, CropField, SearchModelChoiceField, \
    MaskedValueTextInput, RatingWidget, fbmc_search_helper
    

STOP_WORDS = ['a', 'able', 'about', 'across', 'after', 'all', 'almost', 'also', 
    'am', 'among', 'an', 'and', 'any', 'are', 'as', 'at', 'be', 'because', 
    'been', 'but', 'by', 'can', 'cannot', 'could', 'dear', 'did', 'do', 'does', 
    'either', 'else', 'ever', 'every', 'for', 'from', 'get', 'got', 'had', 
    'has', 'have', 'he', 'her', 'hers', 'him', 'his', 'how', 'however', 'i', 
    'if', 'in', 'into', 'is', 'it', 'its', 'just', 'least', 'let', 'like', 
    'likely', 'may', 'me', 'might', 'most', 'must', 'my', 'neither', 'no', 
    'nor', 'not', 'of', 'off', 'often', 'on', 'only', 'or', 'other', 'our', 
    'own', 'rather', 'said', 'say', 'says', 'she', 'should', 'since', 'so', 
    'some', 'than', 'that', 'the', 'their', 'them', 'then', 'there', 'these', 
    'they', 'this', 'tis', 'to', 'too', 'twas', 'us', 'wants', 'was', 'we', 
    'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 
    'will', 'with', 'would', 'yet', 'you', 'your']

class ContentGroupModelForm(ModelForm):
    image = forms.ImageField(required=False, 
        widget=admin.widgets.AdminFileWidget)
    class Meta:
        model = ContentGroup
    
class ContentGroupAdmin(admin.ModelAdmin):
    form = ContentGroupModelForm
    def get_urls(self):
        urls = super(ContentGroupAdmin, self).get_urls()
        urls = patterns('',
            (r'^search/$', self.admin_site.admin_view(self.fbmc_search)),
        ) + urls
        return urls
    
    def fbmc_search(self, request):
        """
        Returns a text response for FBModelChoice Field
        """
        q_str, excludes, limit = fbmc_search_helper(request)
        cg = ContentGroup.objects.filter(
            Q(type__contains=q_str) | Q(name__contains=q_str)) \
            .exclude(pk__in=excludes).order_by('-pk')[:limit]
        return render_to_response('fbmc_result_list.txt', {'objs': cg})

admin.site.register(ContentGroup, ContentGroupAdmin)


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
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        add_rel=ContentGeneric._meta.get_field('contributors').rel
    )
    issue = IssuePickerField(label='Issue Date', required=True)
    slug = forms.SlugField(
        help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed",
        widget=AutoGenSlugWidget(attrs={'size': '40'})
    )
    section = forms.ModelChoiceField(Section.all(), required=True)
    priority = forms.IntegerField(required=False, initial=0,
        help_text='Higher priority articles are displayed first.' \
        'Priority may be positive or negative.')
    group = FbModelChoiceField(required=False, multiple=False,
        url='/admin/content/contentgroup/search/', model=ContentGroup,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        add_rel=ContentGeneric._meta.get_field('group').rel
    )    
    
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
                'group': None,
                'slug': instance.slug,
            }
            if instance.group:
                initial['group'] = instance.group.pk
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
        obj.group = self.cleaned_data['group']
        # can't overwrite slugs
        if not obj.slug:
            obj.slug = self.cleaned_data['slug']
        return obj
    

class ContentGenericAdmin(admin.ModelAdmin):
    """
    Parent class for ContentGeneric ModelAdmin classes.
    Doesn't actually work by itself.
    """
    def get_urls(self):
        return  patterns('',
            (r'^previews_by_date_tag/$',
                self.admin_site.admin_view(self.previews_by_date_tag)),
            (r'^gen_slug/$', self.admin_site.admin_view(self.gen_slug)),
        ) + super(ContentGenericAdmin, self).get_urls()
    
    def gen_slug(self, request):
        """
        returns a few words corresponding to a unique slug for an issue date
        """
        if request.method != 'POST':
            raise Http404
        dt, text = request.POST.get('date', 0), request.POST.get('text', 0)
        if not (dt and text):
            raise Http404
        dt = date(*(strptime(str(dt), r"%m/%d/%Y")[:3]))
        text = text.replace("><", "> <")
        text = html.strip_tags(text)
        text = alphanum_only(text.lower())
        words = {}
        for wrd in text.split():
            if wrd not in STOP_WORDS:
                if wrd in words:
                    words[wrd] += 1
                else:
                    words[wrd] = 1
        words = words.items()
        words.sort(lambda x, y: cmp(y[1], x[1]))
        words = [w[0] for w in words[:3]]
        # TODO: make sure the slug is valid
        return HttpResponse('-'.join(words))
    
    def previews_by_date_tag(self, request):
        """
        returns json of previews, for the SearchModelChoiceField
        """
        OBJS_PER_REQ = 10
        
        tags, start_d, end_d, page = [request.GET.get(x, None) \
            for x in ['tags', 'start_d', 'end_d', 'page']]
        start_d = datetime.strptime(start_d, '%m/%d/%Y') if start_d else None
        end_d = datetime.strptime(end_d, '%m/%d/%Y') if end_d else None
        objs = self.model.find_by_date(start=start_d, end=end_d)
        if tags:
            tags = [t for t in tags.split(',') if t]
            q = reduce(lambda x,y: x and y, 
                [Q(generic__tags__text__icontains=t) for t in tags])
            objs = objs.filter(q)
        p = Paginator(objs, OBJS_PER_REQ).page(page if page else 1)
        
        json_dict = {}
        json_dict['objs'] = {}
        for obj in p.object_list:
            html = '<span>%s</span>' % obj._render("admin.line_item")
            json_dict['objs'][obj.pk] = html
        if not p.object_list:
            json_dict['objs']['empty'] = 1
        json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
        json_dict['prev_page'] = p.previous_page_number() \
            if p.has_previous() else 0
        
        return HttpResponse(simplejson.dumps(json_dict))

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
    huid = forms.fields.CharField(label='HUID', required=False,
        widget=MaskedValueTextInput(sentinel="********"))
    profile_pic = forms.fields.ImageField(widget=admin.widgets.AdminFileWidget,
        required=False, label='Profile Picture')

    def clean_huid(self):
        h = self.cleaned_data['huid']
        if h and len(h) != 8:
            raise forms.ValidationError('HUID must be 8 digits long')
        return self.cleaned_data['huid']
    

class ContributorAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name',)
    fieldsets = (
        (None, {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
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
                ('board_number', 'class_of', 'concentration'),
                'huid',
                ('profile_text', 'profile_pic'),
            )
        }),
    )
    form = ContributorForm
    
    def get_form(self, request, obj=None, **kwargs):
        f = super(ContributorAdmin, self).get_form(request, obj, **kwargs)
        if obj and obj.user and obj.user.get_profile():
            f.base_fields['huid'].initial = obj.user.get_profile().huid_hash
        return f
    
    def save_model(self, request, obj, form, change):
        # create a user if one does not exist
        # then set the groups of the user
        boards = form.cleaned_data['boards']
        if obj.user is None and boards != []:
            u = User()
            u.save()
            ud = UserData(user=u)
            class_of = form.cleaned_data['class_of']
            if class_of is None:
                class_of = 0  
            u.username = ('%s_%s_%s_%d' % (
                form.cleaned_data['first_name'],
                form.cleaned_data['middle_name'],
                form.cleaned_data['last_name'],
                class_of
            ))[:30]
            u.set_unusable_password() # auth is done with Harv PIN
            u.is_staff = True
            u.save()
            ud.save()
            obj.user = u
        if obj.user is not None:
            groups = [board.group for board in boards]
            obj.user.groups = groups
            obj.user.save()
            ud = obj.user.get_profile()
            if ud is None:
                ud = UserData(user=obj.user)
            h = form.cleaned_data['huid']
            if h != "********":
                if h:
                    huid_hash = md5_constructor(h).hexdigest()
                else:
                    huid_hash = None                                                                        
                ud.huid_hash = huid_hash
            ud.save()
        return super(ContributorAdmin, self).save_model(
            request, obj, form, change)
    
    def get_urls(self):
        urls = patterns('',
            (r'^search/$', 
                self.admin_site.admin_view(self.get_contributors)),
        ) + super(ContributorAdmin, self).get_urls()
        return urls
    
    def get_contributors(self, request):
        q_str, excludes, limit = fbmc_search_helper(request)
        c = Contributor.objects.filter(
            Q(first_name__contains=q_str) | Q(last_name__contains=q_str),
            is_active=True).exclude(pk__in=excludes)[:limit]
        return render_to_response('ajax/contributors.txt', {'contributors': c})

admin.site.register(Contributor, ContributorAdmin)


class IssueAdmin(admin.ModelAdmin):
    list_display = ('issue_date',)
    search_fields = ('issue_date',)
    fields = ('issue_date', 'web_publish_date', 'special_issue_name', 
        'fm_name', 'arts_name', 'comments',)
        
    def get_urls(self):
        urls = patterns('',
            (r'^special_issue_list/$', 
                self.admin_site.admin_view(self.get_special_issues)),
        ) + super(IssueAdmin, self).get_urls()
        return urls
        
    def get_special_issues(self, request):
        """
        Returns an html fragment with special issues as <options>
        """
        if request.method != 'GET':
            raise Http404
        year = request.GET.get('year', '')
        if not year.isdigit():
            raise Http404
        year = int(year)
        issues = Issue.objects.special.filter(issue_date__year=year)
        return render_to_response('ajax/special_issues_fragment.html', 
            {'issues': issues, 'blank': '----'})
    

admin.site.register(Issue, IssueAdmin)


class ImageAdminForm(ContentGenericModelForm):
    class Meta:
        model = Image
    
    # the different sizes to crop. these should all be square sizes
    CROP_SIZES = (Image.SIZE_THUMB, Image.SIZE_TINY, Image.SIZE_SMALL)
    
    caption = forms.fields.CharField(required=False,
        widget=forms.Textarea(attrs={'rows':'5', 'cols':'40'})
    )
    thumbnail = CropField(required=False, crop_size=Image.SIZE_THUMB,
        display_size=Image.SIZE_STAND
    )
    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/image/gen_slug/',
            date_field='#id_issue', text_field='#id_caption',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
    
    def save(self, *args, **kwargs):
        i = super(ImageAdminForm, self).save(*args, **kwargs)
        # logic for saving the cropped stuffs
        data = self.cleaned_data['thumbnail']
        if data:
            # crop all the relavent sizes
            for size in ImageAdminForm.CROP_SIZES:
                hori_ratio = float(i.pic.width) / float(Image.SIZE_STAND[0])
                vert_ratio = float(i.pic.height) / float(Image.SIZE_STAND[1])
                # ratio the image is actually scaled at
                scale_ratio = max(hori_ratio, vert_ratio)
                # if this ratio is < 1, then the image wasn't scaled at all
                if scale_ratio < 1.0:
                    scale_ratio = 1
                crop_data = [int(x * scale_ratio) for x in data]
                i.crop_thumb(size, crop_data)
        return i

class ImageAdmin(ContentGenericAdmin):
    fields = ('pic', 'thumbnail', 'caption', 'kicker', 'section', 'issue',
        'slug', 'priority', 'contributors', 'tags', 'group',)
    
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


class ImageGalleryForm(ContentGenericModelForm):
    images = SearchModelChoiceField(
        ajax_url='/admin/content/image/previews_by_date_tag/',
        multiple=True, model=Image, label='', clean_to_objs=True
    )
    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/article/gen_slug/',
            date_field='#id_issue', text_field='#id_description',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
        
    class Meta:
        model = ImageGallery
    
    def save(self, *args, **kwargs):
        imgs = self.cleaned_data.pop('images', [])
        obj = super(ImageGalleryForm, self).save(*args, **kwargs)
        obj.images.clear()
        for i, img in enumerate(imgs):
            x = GalleryMembership(order=i, image_gallery=obj, image=img)
            x.save()
        return obj
    

class ImageGalleryAdmin(ContentGenericAdmin):
    fieldsets = (
        (None, {
            'fields': ('title', 'description',),
        }),
        ('Images', {
            'fields': ('images',),
        }),
        ('Contributors', {
            'fields': ('contributors',),
        }),
        ('Organization', {
            'fields': ('section', 'issue', 'slug', 'tags', 'priority',),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        }),
    )
    form = ImageGalleryForm
    
    class Media:
        css = {'all': ('css/admin/ImageGallery.css',)}
        js = ('scripts/jquery.js',)
    


admin.site.register(ImageGallery, ImageGalleryAdmin)


class ArticleForm(ContentGenericModelForm):
    teaser = forms.fields.CharField(
        widget=forms.Textarea(attrs={'rows':'5', 'cols':'67'}),
        required=False, help_text="""
        A short sample from the article, or a summary of the article. <br>
        If you don't provide a teaser, we will automatically generate one 
        for you.
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
    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/article/gen_slug/',
            date_field='#id_issue', text_field='#id_text',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
    contributors = FbModelChoiceField(required=True, multiple=True,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        #add_rel=Article._meta.get_field('contributors').rel)
        )
    proofer = FbModelChoiceField(required=True, multiple=False,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    sne = FbModelChoiceField(required=True, multiple=False,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    rel_content = RelatedContentField(label='New content', required=False,
        admin_site=admin.site, rel_types=[Image, ImageGallery, Article, Map])
    
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


class ArticleAdmin(ContentGenericAdmin):
    list_display = ('headline', 'section', 'issue',)
    search_fields = ('headline', 'text',)
    exclude = ['is_published']
    fieldsets = (
        ('Headline', {
            'fields': ('headline', 'subheadline',),
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
            'fields': ('slug', 'priority', 'web_only', 'tags',),
        }),
        ('Editing', {
            'fields': ('proofer', 'sne',),
        }),
        ('Associated content', {
            'fields': ('rel_content',),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        })
    )
    form = ArticleForm
    
    class Media:
        js = (
            'scripts/jquery.js',
            'scripts/admin/Article.js',
            'scripts/framework/jquery.sprintf.js',
        )
    
    
    def has_change_permission(self, request, obj=None):
        u = request.user
        if u.is_superuser:
            return True
        # cannot make changes after 60 minutes from uploaded time
        elif obj and not u.has_perm('content.article.can_change_after_timeout'):
            return (datetime.now() - obj.created_on).seconds < (60 * 60)
        return super(ArticleAdmin, self).has_change_permission(request, obj)
    
    def queryset(self, request):
        u = request.user
        qs = super(ArticleAdmin,self).queryset(request)
        if u.is_superuser:
            return qs
       
        # restrict editing of articles uploaded before 60 min ago
        if not u.has_perm('content.article.can_change_after_timeout'):
            t = datetime.now() - timedelta(seconds=(60*60))
            qs = qs.filter(created_on__gt=t)
            u.message_set.create(message='Note: you can only change articles' \
                                            ' uploaded in the last hour.')
        return qs
    
    def get_urls(self):
        urls = super(ArticleAdmin, self).get_urls()
        urls = patterns('',
            (r'^rel_content/get/(?P<ct_id>\d+)/(?P<obj_id>\d+)/$',
                self.admin_site.admin_view(self.get_rel_content)),
            (r'^rel_content/get/(?P<ct_name>\w+)/(?P<obj_id>\d+)/$',
                self.admin_site.admin_view(self.get_rel_content)),
            (r'^rel_content/find/(\d+)/(\d\d/\d\d/\d{4})/(\d\d/\d\d/\d{4})/([\w\-,]*)/(\d+)/$',
                self.admin_site.admin_view(self.find_rel_content)),
        ) + urls
        return urls
    
    def get_rel_content(self, request, obj_id, ct_id=0, ct_name=None):
        """
        returns HTML with a Content obj rendered as 'admin.line_item'
        @ct_id : ContentType pk
        @obj_id : Content pk
        @ct_name : Name of the ContentType. This overrides @ct_id.
        """
        if not ct_id:
            if not ct_name:
                raise Http404
            ct = ContentType.objects.get(
                app_label='content', model=ct_name.lower())
            ct_id = ct.pk
        r = get_object_or_404(
            ContentGeneric, content_type__pk=int(ct_id), object_id=int(obj_id)
        )
        json_dict = {
            'html': mark_safe(r.content_object._render('admin.line_item')),
            'ct_id': ct_id,
        }
        return HttpResponse(simplejson.dumps(json_dict))
    
    def find_rel_content(self, request, ct_id, st_dt, end_dt, tags, page):
        """
        returns JSON containing Content objects and pg numbers
        """
        OBJS_PER_REQ = 3
        
        cls = get_object_or_404(ContentType, pk=int(ct_id))
        cls = cls.model_class()
        st_dt = datetime.strptime(st_dt, '%m/%d/%Y')
        end_dt = datetime.strptime(end_dt, '%m/%d/%Y')
        objs = cls.find_by_date(start=st_dt, end=end_dt)
        p = Paginator(objs, OBJS_PER_REQ).page(page)
        
        json_dict = {}
        json_dict['objs'] = []
        for obj in p.object_list:
            html = '<li>%s</li>' % obj._render("admin.thumbnail")
            html = render_to_string('content_thumbnail.html', {'objs': [obj]})
            json_dict['objs'].append([ct_id, obj.pk, html])
        json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
        json_dict['prev_page'] = p.previous_page_number() \
            if p.has_previous() else 0
        
        return HttpResponse(simplejson.dumps(json_dict))
    

admin.site.register(Article, ArticleAdmin)


class ReviewAdmin(admin.ModelAdmin):
    radio_fields = {"rating": admin.HORIZONTAL}

admin.site.register(Review, ReviewAdmin)


admin.site.register(Score)


class MarkerInline(admin.TabularInline):
    model = Marker
    extra = 3
    fields = ('popup_text','lat','lng')

class MapForm(ContentGenericModelForm):
    map_preview = MapBuilderField(label='Map Preview', required=False)
    
    def __init__(self, *args, **kwargs):
        s = super(MapForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = Map
    

class MapAdmin(ContentGenericAdmin):
    search_fields = ('title','caption',)
    form = MapForm
    
    inlines = [
        MarkerInline,
    ]
    
    fieldsets = (
        ('Map Setup', {
            'fields': ('title', 'caption', 'map_preview'),
        }),
        ('Details', {
            'classes': ('frozen','collapse'),
            'fields': ('zoom_level','center_lng','center_lat','display_mode',
                'width','height',),
        }),
        ('Contributors', {
            'fields': ('contributors',),
        }),
        ('Organization', {
            'fields': ('section', 'issue', 'slug', 'tags', 'priority',),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        }))
    
    class Media:
        js = (
            'scripts/jquery.js',
        )

admin.site.register(Map, MapAdmin)
admin.site.register(Marker)

class HUIDBackend:
    """
    Authenticate HUID (presumably) passed from the Harvard HUID auth thing 
    against the hashed HUID in the Django database.
    """
    def authenticate(self, huid=None):
        # TODO: Implement weird BEGIN PGP SIGNED MESSAGE stuff once we get the 
        # UIS move done and get an actual key and stuff from FASIT.
        huid_hash = md5_constructor(huid).hexdigest()
        try:
            ud = UserData.objects.get(huid_hash=huid_hash)
        except UserData.DoesNotExist:
            return None
        user = ud.user
        return user
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None
    
