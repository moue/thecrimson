from datetime import datetime, timedelta, date
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.contrib.flatpages.models import FlatPage
from crimsononline.core.models import *
from crimsononline.content_module.models import ContentModule
import sys

def index(request):
    issue = Issue.get_current()
    stories = top_articles('News')[:9]
    
    dict = {}
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = top_articles('Opinion')[:6]
    dict['arts'] = top_articles('Arts')[:6]
    dict['sports'] = top_articles('Sports')[:6]
    dict['fms'] = top_articles('News')[:6]
    dict['issue'] = issue
    dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('index.html', dict)

def bigmap(request):
    stories = top_articles('News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('bigmap.html', dict)
    
def article(request, year, month, day, slug):
    year, month, day = int(year), int(month), int(day)
    d = date(year=year, month=month, day=day)
    a = get_object_or_404(Article, generic__issue__issue_date=d, slug=slug)
    nav = a.section.name.lower()
    a.maps.order_by('width') #this looks nicer
    return render_to_response('article.html', {'article': a, 'nav': nav})
    
def writer(request, contributor_id, f_name, m_name, l_name):
    w = get_object_or_404(Contributor, pk=contributor_id)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_initial, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
        
    #TODO: paginate these articles
    content = w.content.all()
    return render_to_response('writer.html', 
                            {'writer': w, 'content': content})

def tag(request, tags):
    tags = tags.lower().replace('_', ' ').split(',')
    content = ContentGeneric.objects.all()
    for tag in tags:
        content = content.filter(tags__text=tag)
    return render_to_response('tag.html', 
        {'tags': tags, 'content': content})

def section(request, section, issue_id=None, tags=None):    
    # validate the section (we don't want /section/balls/ to be a valid url)
    if section == 'photo':
        return photo(request)
    section = filter(lambda x: section.lower() == x.name.lower(), Section.all())
    if len(section) == 0:
        raise Http404
    section = section[0]
    
    # grab the correct issue
    if issue_id is None:
        issue = Issue.get_current()
    else:
        issue = get_object_or_404(Issue, pk=issue_id)
    
    content = ContentGeneric.objects.recent.filter(section__pk=section.pk)
    # filter based on tags
    if tags:
        tags = tags.lower().replace('_',' ').split(',')
        for tag in tags:
            content = content.filter(tags__text=tag)
    content = content[:20]
    
    dict = {
        'nav': section.name.lower(),
        'issue': issue,
        'content': content,
        'section': section.name.capitalize(),
        'tags': tags,
    }
    return render_to_response(
        [dict['nav']+'.html', 'section.html', 'article-list.html'], dict
    )

def image(request, year, month, day, slug):
    year, month, day = int(year), int(month), int(day)
    i = get_object_or_404(Image, created_on__year=year, 
        created_on__month=month, created_on__day=day, slug=slug)
    nav = 'photo'
    return render_to_response('image.html', {'image': i, 'nav': nav})

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

#====== ajax stuff ==========#
def ajax_get_img(request, pk):
    image = get_object_or_404(Image, pk=pk)
    url = image.get_pic_sized_url(500, 500)
    return render_to_response('ajax_get_image.html', locals())
    
    
# =========== view helpers ============== #
def top_articles(section):
    """returns the most recent articles from @section"""
    return Article.objects.recent.filter(generic__section__name=section)