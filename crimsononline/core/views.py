from datetime import datetime, timedelta
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
    stories = Article.recent_objects.filter(section__name='News')[:9]
    
    dict = {}
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = Article.recent_objects.filter(section__name='Opinion')[:6]
    dict['arts'] = Article.recent_objects.filter(section__name='Arts')[:6]
    dict['sports'] = Article.recent_objects.filter(section__name='Sports')[:6]
    dict['fms'] = Article.recent_objects.filter(section__name='News')[:6]
    dict['issue'] = issue
    dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('index.html', dict)

def bigmap(request):
    stories = Article.recent_objects.filter(section__name='News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('bigmap.html', dict)
    
def article(request, year, month, day, slug):
    year, month, day = int(year), int(month), int(day)
    a = get_object_or_404(Article,
        issue__issue_date__year=year, issue__issue_date__month=month,
        issue__issue_date__day=day, slug=slug)
    nav = a.section.name.lower()
    a.maps.order_by('width') #this looks nicer
    return render_to_response('article.html', {'article': a, 'nav': nav})
    
def writer(request, contributor_id, f_name, m_name, l_name):
    w = get_object_or_404(Contributor, pk=contributor_id)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    print (w.first_name, w.middle_initial, w.last_name)
    print (f_name, m_name, l_name)
    if (w.first_name, w.middle_initial, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
        
    #TODO: paginate these articles
    articles = w.article_set.all()
    return render_to_response('writer.html', 
                            {'writer': w, 'articles': articles})

def tag(request, tags):
    tags = tags.lower().replace('_', ' ').split(',')
    articles = Article.objects.all()
    for tag in tags:
        articles = articles.filter(tags__text=tag)
    return render_to_response('tag.html', 
        {'tags': tags, 'articles': articles})

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
    
    #articles = Article.objects.filter(issue=issue.id, section__pk=section.pk)
    articles = Article.recent_objects.filter(section__pk=section.pk)
    # filter based on tags
    if tags is not None:
        tags = tags.lower().replace('_',' ').split(',')
        for tag in tags:
            articles = articles.filter(tags__text=tag)
    articles = articles[:20]
    
    dict = {
        'nav': section.name.lower(),
        'issue': issue,
        'articles': articles,
        'section': section.name.capitalize(),
        'tags': tags,
    }
    return render_to_response(
        [dict['nav']+'.html', 'section.html', 'article-list.html'], dict
    )

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
def get_top_articles(issue_id, section, limit=10):
    """returns the top limit articles from section for the issue"""
    return Article.objects.filter(issue=issue_id, section__name=section) \
        .order_by('-priority')[:limit]