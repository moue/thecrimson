from datetime import datetime, timedelta, date
from re import compile
from time import strptime
from itertools import *
import copy
import re

from django import forms
from django.core import exceptions
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

from crimsononline.admin_cust.models import UserData
from crimsononline.content.models import *
from crimsononline.content.forms import *
from crimsononline.common.utils.strings import alphanum_only
from crimsononline.common.utils.html import para_list
from crimsononline.common.forms import \
    FbModelChoiceField, CropField, SearchModelChoiceField, \
    MaskedValueTextInput, RatingWidget, fbmc_search_helper, \
    TinyMCEWidget, FbSelectWidget


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
            Q(type__icontains=q_str) | Q(name__icontains=q_str)) \
            .exclude(pk__in=excludes).order_by('-pk')[:limit]
        return render_to_response('fbmc_result_list.txt', {'objs': cg})

admin.site.register(ContentGroup, ContentGroupAdmin)


class ContentModelForm(ModelForm):
    """Parent class for Content model forms.
    
    Doesn't actually work by itself.
    """
    
    tags = forms.ModelMultipleChoiceField(Tag.objects.all(), required=True,
        widget=admin.widgets.RelatedFieldWidgetWrapper(
            admin.widgets.FilteredSelectMultiple('Tags', False),
            Content._meta.get_field('tags').rel,
            admin.site
        )
    )
    contributors = FbModelChoiceField(required=True, multiple=True,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        add_rel=Content._meta.get_field('contributors').rel
    )
    
    issue = IssuePickerField(label='Issue Date', required=True)
    
    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/article/gen_slug/',
            date_field='#id_issue_input', text_field='#id_text',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
    section = forms.ModelChoiceField(Section.all(), required=True)
    priority = forms.ChoiceField(choices=Content.PRIORITY_CHOICES, 
        required=False, initial=4, help_text='Higher priority articles are '
        'displayed first. Priority may be positive or negative.'
    )
    group = FbModelChoiceField(required=False, multiple=False,
        url='/admin/content/contentgroup/search/', model=ContentGroup,
        labeler=(lambda obj: str(obj)), admin_site=admin.site,
        add_rel=Content._meta.get_field('group').rel
    )
    rotatable = forms.ChoiceField(Content.ROTATE_CHOICES, required=True,
        label="Place in rotators?", help_text="<b>Make sure this is / has an "
        "image before you set this to rotate!</b>"
    )
    pub_status = forms.ChoiceField(Content.PUB_CHOICES, required=True, 
        label="Published Status", help_text="Only execs can publish content."
    )
    
    model = Content


class ContentAdmin(admin.ModelAdmin):
    """Parent class for Content ModelAdmin classes.
    
    Doesn't actually work by itself.
    """
    
    ordering = ('-issue__issue_date',)
    
    def get_form(self, request, obj=None):
        f = super(ContentAdmin, self).get_form(request, obj)
        
        slug = f.base_fields['slug'].widget
        issue = f.base_fields['issue'].widget
        if obj is not None and obj.pub_status is 1:
            slug.editable = False
            issue.editable = False
        else:
            slug.editable = True
            issue.editable = True
        
        # people that can't add contributors can't add them in the
        #   article interface
        if not request.user.has_perm('content.add_contributor'):
            w = f.base_fields['contributors'].widget
            if not isinstance(w, FbSelectWidget):
                f.base_fields['contributors'].widget = w.widget
        
        if request.user.has_perm('content.delete_content'):
            f.base_fields['pub_status'].widget.choices = Content.PUB_CHOICES
        elif request.user.has_perm('content.content.can_publish'):
            f.base_fields['pub_status'].widget.choices = \
                ((0, 'Draft'), (1, 'Published'),)
        else:
            f.base_fields['pub_status'].widget.choices = ((0, 'Draft'),)
        return f
    
    def save_model(self, request, obj, form, change):
        # don't let anyone change issue / slug on published content.  
        if change and obj and obj.pub_status == 1:
            old_obj = self.model.objects.all_objects().get(pk=obj.pk)
            obj.issue = old_obj.issue
            obj.slug = old_obj.slug
            # don't let nonpermissioned users publish articles
            if old_obj.pub_status != 1 and not \
                request.user.has_perm('content.content.can_publish'):
                raise exceptions.SuspiciousOperation()
        
        # don't let unpermissioned users delete content
        if not request.user.has_perm('content.content.can_delete') and \
            form.cleaned_data['pub_status'] is -1:
            raise exceptions.SuspiciousOperation()
        super(ContentAdmin, self).save_model(request, obj, form, change)
    
    def get_urls(self):
        return patterns('',
            (r'^previews_by_date_tag/$',
                self.admin_site.admin_view(self.previews_by_date_tag)),
            (r'^gen_slug/$', self.admin_site.admin_view(self.gen_slug)),
        ) + super(ContentAdmin, self).get_urls()
    
    def gen_slug(self, request):
        """
        returns a few words corresponding to a unique slug for an issue date
        """
        if request.method != 'POST':
            raise Http404
        dt, text = request.POST.get('date', 0), request.POST.get('text', 0)
        a = request.POST.getlist('text')
        text = a[0]
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
        words = [w[0] for w in words[:4]]
        # TODO: make sure the slug is valid (unique)
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
                [Q(tags__text__icontains=t) for t in tags])
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
    
    def queryset(self, request):
        if request.user.has_perm('content.delete_content'):
            return self.model._default_manager.all_objects()
        elif request.user.has_perm('content.content.can_publish'):
            return self.model._default_manager.get_query_set()
        else:
            return self.model._default_manager.admin_objects()
    

class TagForm(forms.ModelForm):
    ALLOWED_REGEXP = compile(r'[A-Za-z\s\']+$')
    
    class Meta:
        model = Tag
    
    def clean_text(self):
        text = self.cleaned_data['text']
        if not TagForm.ALLOWED_REGEXP.match(text):
            raise forms.ValidationError(
                'Tags can only contain letters and spaces')
        return text
    

class TagAdmin(admin.ModelAdmin):
    form = TagForm
    search_fields = ['text',]
    ordering = ['text',]

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
    list_display =  ('last_name', 'first_name', 'middle_name', 'class_of',
                    'created_on', 'email', 'is_active')
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
                ('board_number', 'class_of'),
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
            obj.userdata = ud
        if obj.user is not None:
            # set the groups
            groups = [board.group for board in boards]
            obj.user.groups = groups
            obj.user.save()
            
            # set the HUID
            ud = obj.userdata
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
            Q(first_name__icontains=q_str) | Q(last_name__icontains=q_str),
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


class ImageAdminForm(ContentModelForm):
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
        url='/admin/content/article/gen_slug/',
            date_field='#id_issue_input', text_field='#id_caption',
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
    

class ImageAdmin(ContentAdmin):
    def pub_status_text(self, obj):
        return Content.PUB_CHOICES[obj.pub_status][1]
    
    pub_status_text.short_description = 'Status'
    
    list_display = ('pk', 'kicker', 'section', 'issue', 'pub_status_text',)
    search_fields = ('kicker', 'caption',)
    ordering = ('-id',)    

    fieldsets = (
        ('Image Setup', {
            'fields': ('pic', 'thumbnail','caption','kicker'),
        }),
        ('Byline', {
            'fields': ('contributors',),
        }),
        ('Print', {
            'fields': ('issue', 'section',),
        }),
        ('Web', {
            'fields': ('pub_status', 'priority', 'slug', 'tags', 'rotatable',),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        })
    )    

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


class GalleryForm(ContentModelForm):
    contents = RelatedContentField(label='Contents', required=False,
        admin_site=admin.site, rel_types=[Image, YouTubeVideo])

    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/article/gen_slug/',
            date_field='#id_issue', text_field='#id_description',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
        
    class Meta:
        model = Gallery
    
    

class GalleryAdmin(ContentAdmin):
    fieldsets = (
        ('Gallery Setup', {
            'fields': ('title','description'),
        }),
        ('Images', {
            'fields': ('contents',)
        }),
        ('Byline', {
            'fields': ('contributors',),
        }),
        ('Print', {
            'fields': ('issue', 'section',),
        }),
        ('Web', {
            'fields': ('pub_status', 'priority', 'slug', 'tags', 'rotatable',),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        })
    )

    form = GalleryForm
    
    class Media:
        css = {'all': ('css/admin/ImageGallery.css',)}
        js = ('scripts/jquery.js',)
    
    def save_model(self, request, obj, form, change):
        contents = form.cleaned_data.pop('contents', [])
        super(GalleryAdmin, self).save_model(request, obj, form, change)
        obj.contents.clear()
        for i, content in enumerate(contents):
            x = GalleryMembership(order=i, gallery=obj, content=content)
            x.save()
        return obj
    

admin.site.register(Gallery, GalleryAdmin)

TEASER_RE = re.compile(r"<\s*\/?\w.*?>") # tags
class ArticleForm(ContentModelForm):
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
        widget=TinyMCEWidget(attrs={'cols':'67','rows':'40'})
    )
    corrections = forms.ModelChoiceField(queryset = Section.all(), required=False)
    proofer = FbModelChoiceField(required=False, multiple=False,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    sne = FbModelChoiceField(required=False, multiple=False,
        url='/admin/content/contributor/search/', model=Contributor,
        labeler=(lambda obj: str(obj)))
    rel_content = RelatedContentField(label='New content', required=False,
        admin_site=admin.site, rel_types=[Image, Gallery, Article, Map, FlashGraphic, YouTubeVideo])
    
    def clean_teaser(self):
        """Add a teaser if one does not exist."""
        if self.cleaned_data['teaser']:
            return self.cleaned_data['teaser']
        else:
            # split article by paragraphs, return first 20 words of first para
            teaser = para_list(self.cleaned_data['text'])[0]
            teaser = TEASER_RE.sub("",teaser)
            return truncatewords(teaser, 20)

    def clean(self):
        self.cleaned_data.pop('corrections')
        return self.cleaned_data
    
    class Meta:
        model = Article


class ArticleAdmin(ContentAdmin):

    def pub_status_text(self, obj):
        return Content.PUB_CHOICES[obj.pub_status][1]
    pub_status_text.short_description = 'Status'

    list_display = ('headline', 'section', 'issue','pub_status_text')
    search_fields = ('headline', 'text',)
    list_filter = ('section',)

    fieldsets = (
        ('Headline', {
            'fields': ('headline', 'subheadline',),
        }),
        ('Text', {
            'fields': ('text', 'teaser', 'corrections'),
        }),
        ('Byline', {
            'fields': ('contributors', 'byline_type',),
        }),
        ('Print', {
            'fields': ('issue', 'section', 'page',),
        }),
        ('Associated content', {
            'fields': ('rel_content',),
        }),
        ('Web', {
            'fields': ('pub_status', 'priority', 'slug', 'tags', 
                        'rotatable', 'web_only'),
        }),
        ('Editing', {
            'fields': ('proofer', 'sne',),
            'classes': ('collapse',),
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
            'scripts/tiny_mce/tiny_mce.js'
        )

    def get_form(self, request, obj=None):
        f = super(ArticleAdmin, self).get_form(request, obj)
        if obj is not None:
            f.base_fields['corrections'].widget.choices = tuple([(x, x.pk) for x in Correction.objects.filter(article = obj)])
        else:
            f.base_fields['corrections'].widget.choices = []
        return f
        
    def has_change_permission(self, request, obj=None):
        u = request.user
        if u.is_superuser:
            return True
        # cannot make change to published stuff; must use corrections interface
        if obj and obj.pub_status != 0:
            return u.has_perm('content.content.can_publish')
        return super(ArticleAdmin, self).has_change_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        rel = form.cleaned_data.pop('rel_content',[])
        
        super(ArticleAdmin, self).save_model(request, obj, form, change)
        obj.rel_content.clear()
        for i, r in enumerate(rel):
            x = ArticleContentRelation(order=i, article=obj, related_content=r)
            x.save()
            
        return obj
    
    def get_urls(self):
        urls = super(ArticleAdmin, self).get_urls()
        urls = patterns('',
            (r'^rel_content/get/(?P<obj_id>\d+)/$',
                self.admin_site.admin_view(self.get_rel_content)),
            (r'^rel_content/get/(?P<obj_id>\d+)/$',
                self.admin_site.admin_view(self.get_rel_content)),
            (r'^rel_content/find/(\d+)/(\d\d/\d\d/\d{4})/(\d\d/\d\d/\d{4})/([\w\-,]*)/(\d+)/$',
                self.admin_site.admin_view(self.find_rel_content)),
            (r'^rel_content/suggest/(\d+)/([\d,]*)/(\d+)/$',
                self.admin_site.admin_view(self.suggest_rel_content)),
        ) + urls
        return urls
    
    def get_rel_content(self, request, obj_id):
        """
        returns HTML with a Content obj rendered as 'admin.line_item'
        @obj_id : Content pk
        """

        r = get_object_or_404(Content, pk=int(obj_id))
        json_dict = {
            'html': mark_safe(r._render('admin.line_item')),
        }
        return HttpResponse(simplejson.dumps(json_dict))
    
    def find_rel_content(self, request, ct_id, st_dt, end_dt, tags, page):
        """
        returns JSON containing Content objects and pg numbers
        """
        OBJS_PER_REQ = 3
        if int(ct_id) != 0:
            cls = ContentType.objects.get(pk=ct_id).model_class()
        else:
            cls = None
        st_dt = datetime.strptime(st_dt, '%m/%d/%Y')
        end_dt = datetime.strptime(end_dt, '%m/%d/%Y')
        if cls:
            objs = cls.find_by_date(start=st_dt, end=end_dt)
        else:
            objs = Content.find_by_date(start=st_dt, end=end_dt)
        
        p = Paginator(objs, OBJS_PER_REQ).page(page)
        
        json_dict = {}
        json_dict['objs'] = []
        for obj in p.object_list:
            html = '<li>%s</li>' % obj._render("admin.thumbnail")
            html = render_to_string('content_thumbnail.html', {'objs': [obj]})
            json_dict['objs'].append([obj.pk, html])
        json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
        json_dict['prev_page'] = p.previous_page_number() \
            if p.has_previous() else 0
        
        return HttpResponse(simplejson.dumps(json_dict))
        
    def suggest_rel_content(self, request, ct_id, tags, page):
        """
        returns JSON containing Content objects and pg numbers
        """
        OBJS_PER_REQ = 3
        
        # intersection between multiple lists using reduce
        def intersect(lists):
            return list(reduce(set.intersection, (set(l) for l in lists)))
        
        # can't really suggest if they don't give you any tags
        if tags == "":
            json_dict = {}
            json_dict['objs'] = []
            return HttpResponse(simplejson.dumps(json_dict))
        
        tags = tags.split(",");
        tagarticles = []
        newerthan = date.today() + timedelta(days=-365)
        for tag in tags:
            # Filter by content type ID only if they didn't search for all types of content
            if ct_id == "0":
                tagarticles.append(Content.objects.filter(issue__issue_date__gte = newerthan).filter(tags__pk = tag))
            else:
                tagarticles.append(Content.objects.filter(issue__issue_date__gte = newerthan).filter(content_type__pk = ct_id).filter(tags__pk = tag))

        objstemp = []
        # Iterate through from most to least matches on tags
        for i in range(len(tagarticles),0,-1):
            combs = combinations(tagarticles, i)
            for comb in combs:
                inter = (intersect(comb))
                for inte in inter:
                    if inte not in objstemp:
                        objstemp.append(inte)
        
        objs = []
        for o in objstemp:
            objs.append(o)

        p = Paginator(objs, OBJS_PER_REQ).page(page)

        json_dict = {}
        json_dict['objs'] = []
        for obj in p.object_list:
            html = render_to_string('content_thumbnail.html', {'objs': [obj]})
            json_dict['objs'].append([obj.pk, html])
        json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
        json_dict['prev_page'] = p.previous_page_number() \
            if p.has_previous() else 0
        return HttpResponse(simplejson.dumps(json_dict))

admin.site.register(Article, ArticleAdmin)


class ReviewAdmin(admin.ModelAdmin):
    radio_fields = {"rating": admin.HORIZONTAL}

admin.site.register(Review, ReviewAdmin)

class YouTubeVideoForm(ContentModelForm):
    pub_status = forms.ChoiceField(Content.PUB_CHOICES,required=True, 
        label="Published Status")

    def __init__(self, *args, **kwargs):
        s = super(YouTubeVideoForm, self).__init__(*args, **kwargs)

    class Meta:
        model = YouTubeVideo
    
class YouTubeVideoAdmin(ContentAdmin):
    form = YouTubeVideoForm

    fieldsets = (
        ('Video Setup', {
            'fields': ('title', 'description', 'key',),
        }),
        ('Byline', {
            'fields': ('contributors',),
        }),
        ('Publishing', {
            'fields': ('issue', 'section', 'pub_status', 'priority', 'slug', 'tags', 'rotatable'),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        })
    )

    class Media:
        js = (
            'scripts/jquery.js',
        )

admin.site.register(YouTubeVideo, YouTubeVideoAdmin)


class FlashGraphicForm(ContentModelForm):
    def __init__(self, *args, **kwargs):
        s = super(FlashGraphicForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FlashGraphic
    
class FlashGraphicAdmin(ContentAdmin):
    form = FlashGraphicForm

    fieldsets = (
        ('Graphic Setup', {
            'fields': ('graphic', 'title', 'description', 'width', 'height'),
        }),
        ('Byline', {
            'fields': ('contributors',),
        }),
        ('Publishing', {
            'fields': ('issue', 'section', 'pub_status', 'priority', 'slug', 'tags', 'rotatable'),
        }),
        ('Grouping', {
            'fields': ('group',),
            'classes': ('collapse',),
        })
    )

    class Media:
        js = (
            'scripts/jquery.js',
        )

admin.site.register(FlashGraphic, FlashGraphicAdmin)

admin.site.register(Score)


class MarkerInline(admin.TabularInline):
    model = Marker
    extra = 3
    fields = ('popup_text','lat','lng')

class MapForm(ContentModelForm):
    map_preview = MapBuilderField(label='Map Preview', required=False)
    slug = forms.fields.SlugField(widget=AutoGenSlugWidget(
            url='/admin/content/article/gen_slug/',
            date_field='#id_issue', text_field='#id_title',
            attrs={'size': '40'},
        ), help_text="This is the text that goes in the URL.  Only letters," \
        "numbers, _, and - are allowed"
    )
    
    class Meta:
        model = Map
    

class MapAdmin(ContentAdmin):
    search_fields = ('title','caption',)
    form = MapForm
    
    inlines = [MarkerInline,]
    
    fieldsets = (
        ('Map Setup', {
            'fields': ('title', 'caption', 'map_preview'),
        }),
        ('Details', {
            'classes': ('frozen','collapse'),
            'fields': ('zoom_level','center_lng','center_lat','display_mode',),
        }),
        ('Contributors', {
            'fields': ('contributors',),
        }),
        ('Organization', {
            'fields': ('section', 'pub_status', 'issue', 'slug', 'tags', 'priority','rotatable'),
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
    
