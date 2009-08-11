import sys
import re
from django.utils import simplejson
from StringIO import StringIO
from datetime import datetime, timedelta, date
from django.shortcuts import get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.contrib.flatpages.models import FlatPage
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import connection
from django.db.models import Count, Max
from django.views.generic.simple import direct_to_template
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from crimsononline.common.utils.paginate import paginate
from crimsononline.common.utils.strings import strip_commas
from crimsononline.common.forms import DateSelectWidget
from crimsononline.common.templatetags.common import human_list

def get_content(request, ctype, year, month, day, slug, content_group=None):
    """
    View for displaying a piece of content on a page
    Validates the entire URL
    """
    c = get_content_obj(request, ctype, year, month, day, slug, content_group)
    # redirect to canonical URL
    if request.path != c.get_absolute_url():
        return HttpResponseRedirect(c.get_absolute_url())
    if request.method == 'GET':
        return HttpResponse(c._render(request.GET.get('render','page'), request=request))
    return Http404

def get_content_obj(request, ctype, year, month, day, slug, content_group=None):
    """
    Retrieves a content object from the database (no validation of params)
    """
    ctype = ctype.replace('-', ' ') # convert from url
    c = Content.objects.get(issue__issue_date=date(int(year), int(month), int(day)), slug=slug
    )
    return c
    
def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug):
    """
    View for displaying a piece of grouped content on a page
    Validates the entire url
    """
    # validate the contentgroup
    cg = get_grouped_content_obj(request, gtype, gname, ctype, 
        year, month, day, slug)
    if cg:
        return get_content(request, ctype, year, month, day, slug, cg)
    else:
        raise Http404

def get_grouped_content_obj(request, gtype, gname, ctype, year, month, day, slug):
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
    c = cg.content.all()
    return direct_to_template(request,'contentgroup.html', {'cg': cg, 'content': c})

def get_content_group_obj(request, gtype, gname):
    cg = ContentGroup.by_name(gtype, gname)
    return cg

def index(request, m=None, d=None, y=None):
    stories = top_articles('News')
    
    dt = None
    # if viewing an issue, try to form date, if not successful, 404
    if(m != None):
        try:
            dt = datetime(int(y), int(m), int(d))
        except:
            raise Http404

            
    # Filter stories if we have a past issue date
    if(dt != None):
        stories = stories.filter(issue__issue_date__lte = dt)
    else:
        m = date.today().month
        d = date.today().day
        y = date.today().year

    dict = {}
    
    # right now, this includes deleted stuff. this query already needed to be reworked, but now tha'ts even more important
    dict['rotate'] = stories.filter(rotatable=3)[:4]
    
    dict['past_issues'] = DateSelectWidget().render(name="past_issues", value=[m, d, y])
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = top_articles('Opinion', dt)[:4]
    dict['arts'] = top_articles('Arts', dt)[:4]
    dict['sports'] = top_articles('Sports', dt)[:4]
    dict['fms'] = top_articles('FM', dt)[:4]
    dict['issue'] = Issue.get_current()
    #dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return direct_to_template(request,'index.html', dict)

def bigmap(request):
    stories = top_articles('News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return direct_to_template(request, 'bigmap.html', dict)
    
REMOVE_P_RE = re.compile(r'page/\d+/$')
def writer(request, pk, f_name, m_name, l_name, 
    section_str='', type_str='', page=1):
    
    w = get_object_or_404(Contributor, pk=pk)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_name, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
    
    f = filter_helper(w.content.all(), section_str, type_str, 
        w.get_absolute_url())
    
    d = paginate(f.pop('content'), page, 10)
    d.update({'writer': w, 'url': REMOVE_P_RE.sub(request.path, '')})
    d.update(f)
    
    t = 'writer.html'
    if request.GET.has_key('ajax'):
        t = 'ajax/content_list_page.html'
    return direct_to_template(request, t, d)

def tag(request, tag, section_str='', type_str='', page=1):
    tag = get_object_or_404(Tag, text=tag.replace('_', ' '))
    content = Content.objects.filter(tags=tag)
    
    # top articles
    #articles = Content.objects.type(Article).filter(tags=tag)
    articles = Article.objects.filter(tags=tag)
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
    
    # top writers (contributors that have the most content with this tag)
    cursor = connection.cursor()
    cursor.execute("""SELECT
            content_contributors.contributor_id, 
            count(content.id) AS objcount
        FROM 
            content_content AS content,
            content_content_contributors AS content_contributors,
            content_content_tags AS content_tags
        WHERE
            content_contributors.content_id = content.id AND
            content_tags.content_id = content.id AND
            content_tags.tag_id = %i AND
            content.pub_status = 1
        GROUP BY content_contributors.contributor_id 
        ORDER BY objcount DESC 
        LIMIT 5
    """ % tag.pk) # TODO: should actually do this with sqlite3 replacement, not python
    rows = [r for r in cursor.fetchall() if r[1] > 0]
    writers = Contributor.objects.filter(pk__in=[r[0] for r in rows])
    contrib_count = dict(rows)
    for w in writers:
        w.c_count = contrib_count[w.pk]
        w.rece = w.content.recent[:1][0].issue.issue_date
    writers = list(writers)
    writers.sort(lambda x, y: cmp(y.c_count, x.c_count))
    
    # related tags (tags with most shared content)
    #  select the tags for which there are the most objects that have both 
    #  this tag and that tag within some timeframe
    cursor.execute("""SELECT cgt2.tag_id, 
        count(cgt2.content_id) AS o_count  
        FROM content_content_tags AS cgt1 
        JOIN content_content_tags AS cgt2
        ON cgt1.content_id=cgt2.content_id 
        WHERE cgt1.tag_id = %(pk)i AND cgt2.tag_id != %(pk)i 
        GROUP BY cgt2.tag_id ORDER BY o_count DESC LIMIT 15;""" % {'pk': tag.pk}
    )
    rows = cursor.fetchall()
    tags = Tag.objects.filter(pk__in=[r[0] for r in rows])
    tags_count = dict(rows)
    for t in tags:
        t.content_count = tags_count[t.pk]
    tags = list(tags)
    tags.sort(lambda x,y: cmp(y.content_count, x.content_count))
    
    d = paginate(f.pop('content'), page, 10)
    d.update({'tag': tag, 'url': tag.get_absolute_url(), 'tags': tags,
        'featured': [], 'top_contributors': writers,})
    d.update(f)
    
    t = 'tag.html'
    if request.GET.has_key('ajax'):
        t = 'ajax/content_list_page.html'
    return direct_to_template(request, t, d)


def section_news(request):
    nav = 'news'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(section=section)
    rotate = []#stories.filter(
    #rel_content__content_type=Image.content_type()).distinct()[:4]
    stories = stories.exclude(pk__in=[c.pk for c in rotate])[:15]
    
    series = ContentGroup.objects.filter(section=section) \
        .annotate(c_count=Count('content')).filter(c_count__gte=3) \
        .annotate(latest=Max('content__issue__issue_date')) \
        .order_by('-latest')[:2]
    
    return direct_to_template(request,'sections/news.html', locals())
    
def section_opinion(request):
    nav = 'opinion'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(section=section)
    rotate = []#Content.objects.recent \
    #.filter(content_type=Image.content_type()) \
    #.filter(section=section)[:4]
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))
    return direct_to_template(request,'sections/opinion.html', locals())
    
def section_fm(request):
    nav = 'fm'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(section=section)
    scrutiny_key = None
    endpaper_key = None
    try:
        scrutiny_key = stories.filter(tags__text='scrutiny')[0].pk
    except:
        pass
    try:
        endpaper_key = stories.filter(tags__text='endpaper')[0].pk
    except:
        pass
    ex = [scrutiny_key, endpaper_key]
    rotate = []#stories.filter(rel_content__content_type=Image.content_type()) \
    #.distinct()[:4]
    itm = stories.filter(tags__text='itm')[:3]
    ftm = stories.filter(tags__text='ftm')[:9]
    issues = Issue.objects.exclude(fm_name=None).exclude(fm_name='')[:3]
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))
    return direct_to_template(request,'sections/fm.html', locals())
    
def section_arts(request):
    nav = 'arts'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(section=section)
    rotate = []#stories.filter(rel_content__content_type=Image.content_type()) \
    #    .distinct()[:4]
    stories = stories.exclude(pk__in=[s.pk for s in rotate])
    books = stories.filter(tags__text='books')[:4]
    oncampus = stories.filter(tags__text='on campus')[:6]
    music = stories.filter(tags__text='music')[:2]
    visualarts = stories.filter(tags__text='visual arts')[:2]
    issues = Issue.objects.exclude(arts_name=None).exclude(arts_name='')[:3]
    reviews = {}
    for t in ['movie', 'music', 'book']:
        reviews[t] = Review.objects.filter(type=t)[:4]
    return direct_to_template(request,'sections/arts.html', locals())
    
def section_photo(request):
    if request.method == 'GET':
        page = request.GET.get('page', 1)
    else: raise Http404
    nav = 'photo'
    content = Gallery.objects.recent
        
    d = paginate(content, page, 6)
    d.update({'nav': nav})
    
    t = 'sections/photo.html'
    if request.GET.has_key('ajax'):
        t = 'ajax/media_viewer_page.html'
    return direct_to_template(request, t, d)
    
def section_sports(request):
    nav = 'sports'
    section = Section.cached(nav)
    stories = Article.objects.filter(section=section)
    rotate = []#stories.filter(rel_content__content_type=Image.content_type()) \
    #    .distinct()[:4]
    stories = stories.exclude(pk__in=[r.pk for r in rotate])
    return direct_to_template(request, 'sections/sports.html', locals())

# IPHONE APP JSON FEEDS

def iphone(request, s = None):
    if(s == None):
        raise Http404
        
    section = ""
    try:
        section = Section.cached(s)
    except KeyError:
        raise Http404
    stories = Article.objects.recent.filter(section=section)[:15]
    
    objs = []
    for story in stories:
        curdict = {}
        curdict['id'] = story.pk
        curdict['date_and_time'] = story.issue.issue_date.strftime("%I:%M %p, %B %d, %Y").upper()
        curdict['headline'] = story.headline
        curdict['subhead'] = story.subheadline
        curdict['byline'] = human_list(story.contributors.all())
        curdict['article_text'] = story.text
        curdict['photoURL'] = ""
        if story.main_rel_content:
            curdict['thumbnailURL']  = story.main_rel_content.display_url((69, 69, 1, 1))
            curdict['photoURL']  = story.main_rel_content.display_url((280, 240, 1, 1))
            curdict['photo_byline'] = human_list(story.main_rel_content.contributors.all())
        objs.append(curdict)
        
    io = StringIO()
    simplejson.dump(objs, io)
    
    return HttpResponse(io.getvalue(), mimetype='application/json')
    
def photo(request):
    galleries = Gallery.objects.order_by('-created_on')[:10]
    nav, title = 'photo', 'Photo'
    return direct_to_template(request, 'photo.html', locals())

def gallery(request, currentimg_id, gallery_id):
    currentimg_id = int(currentimg_id)
    gallery_id = int(gallery_id)
    image = get_object_or_404(Image, pk=currentimg_id)
    gallery = get_object_or_404(Gallery, pk=gallery_id)
    return direct_to_template(request,'gallery.html', {'currentimg':image, 'gallery':gallery})

#====== ajax stuff ==========#
def ajax_get_img(request, pk):
    image = get_object_or_404(Image, pk=pk)
    url = image.display(500, 500).url
    return direct_to_template(request,'ajax/get_image.html', locals())
    
    
# =========== view helpers ============== #
def filter_helper(qs, section_str, type_str, url_base):
    """
    returns a dictionary with elements necessary for the content_list
        filter interface
    """
    # TODO: refactor the fuck out of this
    unfilteredcontent = qs
    content = qs
    sects, tps = {}, {}
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

        # TODO: cache this shit
        ct = len(unfilteredcontent.filter(section=section))
        sects[section.name] = {'selected': a, 'url': url, 'count': ct} 
        
    if type_str:
        type_str = type_str.replace('-', ' ') # convert from url
        type_str = [t.lower() for t in type_str.split(',') if t]

        types = [t for t in Content.types() if t.name.lower() in type_str]
        content = content.filter(content_type__in=types)
    else:
        type_str = [t.name.lower() for t in Content.types()]
        types = Content.types()
    for type in Content.types():
        tname = type.name.lower()
        a = type in types
        if a:
            t_str = ','.join([t for t in type_str if t != tname])
        else:
            t_str = ','.join(type_str + [tname])
        
        url = url_base
        url += ('sections/%s/' % o_section_str if o_section_str else '')
        url += ('types/%s/' % t_str if t_str else '')

        ct = len(unfilteredcontent.filter(content_type=type))

        tps[tname.title()] = {'selected': a, 'url': url, 'count':ct}
    
    return {'content': content, 'sections': sects, 'types': tps}
    

def top_articles(section, dt = None):
    """returns the most recent articles from @section"""
    stories = Article.objects.filter(section__name=section)

    if(dt != None):
        stories = stories.filter(issue__issue_date__lte = dt)
    return stories

def last_month():
    return date.today() + timedelta(days=-30)

def last_year():
    return date.today() + timedelta(days=-365)