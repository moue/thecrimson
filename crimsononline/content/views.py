import sys
import re
from datetime import datetime, timedelta, date
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.contrib.flatpages.models import FlatPage
from django.contrib.contenttypes.models import ContentType
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from crimsononline.common.utils.paginate import paginate
from crimsononline.common.utils.strings import strip_commas
from django.core.mail import send_mail


def get_content(request, ctype, year, month, day, slug, pk, content_group=None):
    """
    View for displaying a piece of content on a page
    Validates the entire URL
    """
    c = get_content_obj(request, ctype, year, month, day, slug, pk, content_group)
    # redirect to canonical URL
    if request.path != c.get_absolute_url():
        return HttpResponseRedirect(c.get_absolute_url())
    return HttpResponse(c._render('page'))

def get_content_obj(request, ctype, year, month, day, slug, pk, content_group=None):
    """
    Retrieves a content object from the database (no validation of params)
    """
    c = ContentGeneric.objects.get(content_type__name=ctype, object_id=int(pk))
    return c.content_object
    
def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug, pk):
    """
    View for displaying a piece of grouped content on a page
    Validates the entire url
    """
    # validate the contentgroup
    cg = get_grouped_content_obj(request, gtype, gname, ctype, 
        year, month, day, slug, pk)
    if cg:
        return get_content(request, ctype, year, month, day, slug, pk, cg)
    else:
        raise Http404

def get_grouped_content_obj(request, gtype, gname, ctype, year, month, day, slug, pk):
    cg = ContentGroup.by_name(gtype, gname)
    return cg
        
def get_content_group(request, gtype, gname):
    """
    View for a Content Group
    """
    # validate the contentgroup
    cg = get_content_group_obj(request, gtype, gname)
    if not cg:
        raise Http404
    c = cg.contentgeneric_set.all()
    return render_to_response('contentgroup.html', {'cg': cg, 'content': c})

def get_content_group_obj(request, gtype, gname):
    cg = ContentGroup.by_name(gtype, gname)
    return cg

def index(request):
    stories = top_articles('News')
    dict = {}
    
    dict['rotate'] = stories.filter(
        rel_content__content_type=Image.content_type()).distinct()[:4]
    stories = stories.exclude(pk__in=[c.pk for c in dict['rotate']])
    
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = top_articles('Opinion')[:6]
    dict['arts'] = top_articles('Arts')[:6]
    dict['sports'] = top_articles('Sports')[:6]
    dict['fms'] = top_articles('FM')[:6]
    dict['issue'] = Issue.get_current()
    #dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('index.html', dict)

def bigmap(request):
    stories = top_articles('News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('bigmap.html', dict)
    
REMOVE_P_RE = re.compile(r'page/\d+/$')
def writer(request, pk, f_name, m_name, l_name, 
    section_str='', type_str='', page=1):
    
    w = get_object_or_404(Contributor, pk=pk)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_initial, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
    
    f = filter_helper(w.content.all(), section_str, type_str, 
        w.get_absolute_url())
    
    d = paginate(f.pop('content'), page, 10)
    d.update({'writer': w, 'url': REMOVE_P_RE.sub(request.path, '')})
    d.update(f)
    
    return render_to_response('writer.html', d)

def tag(request, tag, section_str='', type_str='', page=1):
    tag = get_object_or_404(Tag, text=tag.replace('_', ' '))
    content = ContentGeneric.objects.filter(tags=tag)
    
    # top articles
    articles = ContentGeneric.objects.type(Article).filter(tags=tag)
    featured_articles = list(articles.filter(
        issue__issue_date__gte=last_month()).order_by('-priority')[:5])
    if len(featured_articles) < 5:
        featured_articles += list(articles.filter(
            issue__issue_date__gte=last_year(), 
            issue__issue_date__lte=last_month()).order_by('-priority')[:5])
    if len(featured_articles) < 5:
        featured_articles += list(articles.filter( 
            issue__issue_date__lte=last_year()).order_by('-priority')[:5])
    featured_articles = featured_articles[:5]
    
    f = filter_helper(content, section_str, type_str, 
        tag.get_absolute_url())
    
    # TODO: top writers (contributors that have the most content with this tag)
    
    
    # TODO: related tags (tags with most shared content)
    #content_pks = [d['id'] for d in content.values('id')]
    #rel_tags = Tag.objects.filter(content__id__in=content_pks).annotate(
    
    
    d = paginate(f.pop('content'), page, 5)
    d.update({'tag': tag, 'url': tag.get_absolute_url(), 
        'featured': featured_articles})
    d.update(f)
    
    return render_to_response('tag.html', d)

def section(request, section):    
    # validate the section (we don't want /section/balls/ to be a valid url)
    if section == 'photo':
        return photo(request)
    section = section.lower()
    section = [s for s in Section.all() if section == s.name.lower()]
    if len(section) != 1:
        raise Http404
    section = section[0]
    
    content = ContentGeneric.objects.recent.filter(section__pk=section.pk)[:20]
    
    dict = {
        'nav': section.name.lower(),
        'content': content,
        'section': section.name.capitalize(),
    }
    return render_to_response(
        [dict['nav']+'.html', 'section.html', 'content_list.html'], dict
    )

def section_news(request):
    nav = 'news'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(generic__section=section)
    rotate = stories.filter(
        rel_content__content_type=Image.content_type()).distinct()[:4]
    stories = stories.exclude(pk__in=[c.pk for c in rotate])[:20]
    
    return render_to_response('sections/news.html', locals())
    
def section_opinion(request):
    nav = 'opinion'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(generic__section=section)
    rotate = ContentGeneric.objects.recent \
        .filter(content_type=Image.content_type()) \
        .filter(section=section)[:4]
    return render_to_response('sections/opinion.html', locals())
    
def section_fm(request):
    nav = 'fm'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(generic__section=section)
    scrutiny = stories.filter(generic__tags__text='scrutiny')[0]
    endpaper = stories.filter(generic__tags__text='endpaper')[0]
    ex = [scrutiny.pk, endpaper.pk]
    rotate = stories.filter(rel_content__content_type=Image.content_type()) \
        .distinct()[:4]
    itm = stories.filter(generic__tags__text='itm')[:3]
    ftm = stories.filter(generic__tags__text='ftm')[:9]
    issues = Issue.objects.exclude(fm_name=None).exclude(fm_name='')[:3]
    return render_to_response('sections/fm.html', locals())
    
def section_arts(request):
    nav = 'arts'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(generic__section=section)
    rotate = stories.filter(rel_content__content_type=Image.content_type()) \
        .distinct()[:4]
    stories = stories.exclude(pk__in=[s.pk for s in rotate])
    books = stories.filter(generic__tags__text='books')[:4]
    oncampus = stories.filter(generic__tags__text='on campus')[:6]
    music = stories.filter(generic__tags__text='music')[:2]
    visualarts = stories.filter(generic__tags__text='visual arts')[:2]
    issues = Issue.objects.exclude(arts_name=None).exclude(arts_name='')[:3]
    return render_to_response('sections/arts.html', locals())
    
def section_photo(request):
    nav = 'photo'
    section = Section.cached(nav)
    content = top_articles(nav)
    return render_to_response('sections/photo.html', locals())
    
def section_sports(request):
    nav = 'sports'
    section = Section.cached(nav)
    content = top_articles(nav)
    return render_to_response('sections/sports.html', locals())

def photo(request):
    galleries = ImageGallery.objects.order_by('-created_on')[:10]
    nav, title = 'photo', 'Photo'
    return render_to_response('photo.html', locals())
    
def gallery(request, currentimg_id, gallery_id):
    currentimg_id = int(currentimg_id)
    gallery_id = int(gallery_id)
    image = get_object_or_404(Image, pk=currentimg_id)
    gallery = get_object_or_404(ImageGallery, pk=gallery_id)
    return render_to_response('gallery.html', {'currentimg':image, 'gallery':gallery})

def subscribe(request):
	if request.method == 'POST':
		form = SubscriptionForm(request.POST)
		if form.is_valid():
			form.save()
			#send_mail('Your Harvard Crimson Subscription', 'yay!', 'subscriptions@thecrimson.com', [form.cleaned_data['email']], fail_silently=False)
			return HttpResponseRedirect('/done')
	else:
		form = SubscriptionForm()
	return render_to_response('subscription.html', {'form': form,})

def subscribed(request):
	return render_to_response('done.html')

#====== ajax stuff ==========#
def ajax_get_img(request, pk):
    image = get_object_or_404(Image, pk=pk)
    url = image.display(500, 500).url
    return render_to_response('ajax/get_image.html', locals())
    
    
# =========== view helpers ============== #

def filter_helper(qs, section_str, type_str, url_base):
    """
    returns a dictionary with elements necessary for the content_list
        filter interface
    """
    # TODO: refactor the fuck out of this
    
    content = qs
    sects, types = {}, {}
    o_section_str = section_str
    
    # parses the comma delimited section_str
    if section_str:
        section_str = [s.lower() for s in section_str.split(',') if s]
        sections = [s for s in Section.all() if s.name.lower() in section_str]
        content = content.filter(section__in=sections)
    else:
        section_str = [s.name.lower() for s in Section.all()]
        sections = Section.all()
    # generates URLs for the different filter links
    for section in Section.all():
        a = section in sections
        if a:
            s_str = ','.join([s for s in section_str if s != section.name.lower()])
        else:
            s_str = ','.join(section_str + [section.name.lower()])
        
        url = url_base 
        url += ('sections/%s/' % s_str if s_str else '')
        url += ('types/%s/' % type_str if type_str else '')
        sects[section.name] = {'selected': a, 'url': url} 
        
    if type_str:
        type_str = [t.lower() for t in type_str.split(',') if t]
        content = content.filter(content_type__name__in=type_str)
    else:
        type_str = [t.name.lower() for t in Content.types()]
    for type in [t.name.lower() for t in Content.types()]:
        a = type in type_str
        if a:
            t_str = ','.join([t for t in type_str if t != type])
        else:
            t_str = ','.join(type_str + [type])
        
        url = url_base
        url += ('sections/%s/' % o_section_str if o_section_str else '')
        url += ('types/%s/' % t_str if t_str else '')
        types[type.title()] = {'selected': a, 'url': url}
    
    return {'content': content, 'sections': sects, 'types': types}
    

def top_articles(section):
    """returns the most recent articles from @section"""
    return Article.objects.recent.filter(generic__section__name=section)

def last_month():
    return date.today() + timedelta(days=-30)

def last_year():
    return date.today() + timedelta(days=-365)