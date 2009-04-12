import sys
from datetime import datetime, timedelta, date
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.contrib.flatpages.models import FlatPage
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule


def get_content(request, ctype, year, month, day, slug, pk, content_group=None):
    c = get_content_obj(request, ctype, year, month, day, slug, pk, content_group)
    return HttpResponse(c._render('page'))

def get_content_obj(request, ctype, year, month, day, slug, pk, content_group=None):
    c = ContentGeneric.objects.get(content_type__name=ctype, object_id=int(pk))
    c = c.content_object
    return c
    
def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug, pk):
    # validate the contentgroup
    cg = get_grouped_content_obj(gtype, gname)
    if cg:
        return get_content(request, ctype, year, month, day, slug, cg)
    else:
        raise Http404

def get_grouped_content_obj(request, gtype, gname, ctype, year, month, day, slug, pk):
    cg = ContentGroup.by_name(gtype, gname)
    return cg
        
def get_content_group(request, gtype, gname):
    # validate the contentgroup
    cg = get_content_group_obj(gtype, gname)
    if not cg:
        raise Http404
    c = cg.contentgeneric_set.all()
    return render_to_response('contentgroup.html', {'cg': cg, 'content': c})

def get_content_group_obj(request, gtype, gname):
    cg = ContentGroup.by_name(gtype, gname)
    return cg

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
    dict['fms'] = top_articles('FM')[:6]
    dict['issue'] = issue
    dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('index.html', dict)


def bigmap(request):
    stories = top_articles('News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('bigmap.html', dict)
    

def writer(request, contributor_id, f_name, m_name, l_name):
    w = get_object_or_404(Contributor, pk=contributor_id)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_initial, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
    #TODO: paginate these articles
    return render_to_response('writer.html', {'writer': w})

def tag(request, tags):
    tag_texts = [t for t in tags.lower().replace('_', ' ').split(',') if t]
    tags = Tag.objects.filter(text__in=tag_texts)
    # there's some tag in the query that doesn't exist.  
    if len(tags_texts) != len(tags):
        tags = None
    q = reduce(lambda x,y: x and y, [Q(tags=tag) for tag in tags])
    content = ContentGeneric.objects.filter(q)
    return render_to_response('tag.html', {'tags': tags, 'content': content})

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
    url = image.display(500, 500).url
    return render_to_response('ajax_get_image.html', locals())
    
    
# =========== view helpers ============== #
def top_articles(section):
    """returns the most recent articles from @section"""
    return Article.objects.recent.filter(generic__section__name=section)