import sys
import re
from django.utils import simplejson
from StringIO import StringIO
from datetime import datetime, timedelta, date
from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Count, Max, Q
from django.views.decorators.cache import cache_page
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from crimsononline.common.caching import funcache as cache
from crimsononline.common.utils.paginate import paginate
from crimsononline.common.utils.strings import strip_commas
from crimsononline.common.utils.lists import first_or_none
from crimsononline.common.forms import DateSelectWidget
from crimsononline.common.templatetags.common import human_list

# ============ ACTUAL VIEWS =====================

@cache_page(settings.CACHE_STANDARD)
def index(request, m=None, d=None, y=None):
    """Show the view for the front page."""
    dt = None
    # if viewing an issue, try to form date, if not successful, 404
    if m is None or d is None or y is None:        
        y, m, d = date.today().timetuple()[:3]
    else:
        try:
            dt = datetime(int(y), int(m), int(d))
            stories = stories.filter(issue__issue_date__lte = dt)
        except:
            # TODO: remove this 404, just say issue not found
            raise Http404
    stories = top_articles('News', dt)
    
    dict = {}
    dict['rotate'] = rotatables(None, 4)
    
    #dict['past_issues'] = DateSelectWidget().render(name="past_issues", 
    #                                                value=[m, d, y])
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = top_articles('Opinion', dt)[:4]
    dict['arts'] = top_articles('Arts', dt)[:4]
    dict['sports'] = top_articles('Sports', dt)[:4]
    dict['fms'] = top_articles('FM', dt)[:4]
    dict['issue'] = Issue.get_current()
    
    return render_to_response('index.html', dict)

REMOVE_P_RE = re.compile(r'page/\d+/$')
@cache_page(settings.CACHE_LONG)
def writer(request, pk, f_name, m_name, l_name, 
    section_str='', type_str='', page=1):
    """Show the view for a specific writer."""
    
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
    return render_to_response(t, d)

@cache_page(settings.CACHE_LONG)
def tag(request, tag, section_str='', type_str='', page=1):
    """Show the view for a specific tag."""
    
    tag = get_object_or_404(Tag, text=tag.replace('_', ' '))
    content = Content.objects.filter(tags=tag)
    f = filter_helper(content, section_str, type_str, 
        tag.get_absolute_url())
    
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
        'featured': featured_articles, 'top_contributors': writers,})
    d.update(f)
    
    t = 'tag.html'
    if request.GET.has_key('ajax'):
        t = 'ajax/content_list_page.html'
    return render_to_response(t, d)

# ============= Section Views ============

@cache_page(settings.CACHE_SHORT)
def section_news(request):
    """Show the view for the news section page."""
    
    nav = 'news'
    section = Section.cached(nav)
    stories = top_articles(section)
    rotate = rotatables(section, 4)
    
    series = ContentGroup.objects.filter(section=section) \
        .annotate(c_count=Count('content')).filter(c_count__gte=3) \
        .annotate(latest=Max('content__issue__issue_date')) \
        .order_by('-latest')[:2]
    
    return render_to_response('sections/news.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_opinion(request):
    """Show the view for the opinion section page."""
    
    nav = 'opinion'
    section = Section.cached(nav)
    stories = top_articles(section)[:10]
    rotate = rotatables(section, 4)
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))
    return render_to_response('sections/opinion.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_fm(request):
    """Show the view for the FM section page.
    
    We want to prioritize articles by date first, since FM is issue
    based.  All FM articles are divided into discrete categories,
        'scrutiny', 'endpaper', 'for the moment', and 'in the meantime'
    (they are differentiated by tags) so we don't have to worry about 
    repeats between the categories.
    """
    
    nav = 'fm'
    section = Section.cached(nav)
    stories = Article.objects.recent.filter(section=section)
    try:
        scrutiny = stories.filter(tags__text='scrutiny')[0]
    except IndexError:
        scrutiny = None
    try:
        endpaper = stories.filter(tags__text='endpaper')[0]
    except IndexError:
        endpaper = None
    rotate = rotatables(section, 4)
    itm = stories.filter(tags__text='itm')[:3]
    ftm = stories.filter(tags__text='ftm')[:9]
    issues = Issue.objects.exclude(Q(fm_name=None)|Q(fm_name=''))[:3]
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))
    return render_to_response('sections/fm.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_arts(request):
    """Show the view for the arts section page."""
    
    nav = 'arts'
    section = Section.cached(nav)
    stories = top_articles(section)
    rotate = rotatables(section)
    books = stories.filter(tags__text='books')[:4]
    oncampus = stories.filter(tags__text='on campus')[:6]
    music = stories.filter(tags__text='music')[:2]
    visualarts = stories.filter(tags__text='visual arts')[:2]
    issues = Issue.objects.exclude(Q(arts_name=None)|Q(arts_name=''))[:3]
    reviews = {}
    for t in ['movie', 'music', 'book']:
        reviews[t] = Review.objects.filter(type=t)[:4]
    return render_to_response('sections/arts.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_photo(request):
    """Show the view for the media section page."""
    
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
    return render_to_response(t, d)

@cache_page(settings.CACHE_SHORT)
def section_sports(request):
    """Show the view for the sports section page.
    
    ** There's tons of crap on this page: **
    Latest updates
        Articles listed by most recently updated (great for live coverage)
    Sports blogs
        Blog content.  Don't worry about articles showing up in two places.
    Athlete of the Week
        An article tagged 'athlete of the week'.  Probably higher priority,
        so, exclude this from top stories
    2 sports features
        TODO: not quite sure how to decide which sports to feature
    Sports tags
        unless we add extra data on tags, we'll have to keep a manual list.
    Latest video
        Bam
    Latest scores
        idk yet
    """
    
    nav = 'sports'
    section = Section.cached(nav)
    stories = top_articles(section)
    rotate = rotatables(section)
    latest = Article.objects.filter(section=section).order_by('-modified_on')
    blog = stories.filter(group__type='blog')
    athlete = first_or_none(stories.filter(tags__text='athlete of the week')) 
    return render_to_response('sections/sports.html', locals())

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

# =========== view helpers ============== #

@cache(settings.CACHE_LONG, "general_content")
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

# no need to cache these two i don't think, since they all go through get_content in the end

def get_content_obj(request, ctype, year, month, day, slug, content_group=None):
    """Retrieve a content object from the database (no validation of params)"""
    ctype = ctype.replace('-', ' ') # convert from url
    c = Content.objects.get(issue__issue_date=date(int(year), int(month), int(day)), slug=slug
    )
    return c
    
def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug):
    """View for displaying a piece of grouped content on a page
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

try:
    FLYBY = ContentGroup.objects.get(name="FlyBy", type="blog")
except:
    FLYBY = ContentGroup.objects.create(name="FlyBy", type="blog")
@cache(settings.CACHE_STANDARD, "general_contentgroup")
def get_content_group(request, gtype, gname):
    """Render a Content Group."""
    # validate the contentgroup
    cg = get_content_group_obj(request, gtype, gname)
    if not cg:
        raise Http404
    c = cg.content.all()
    
    templ = "contentgroup.html"
    if(cg == FLYBY):
        templ = "flyby/content_list.html"
    return render_to_response(templ, {'cg': cg, 'content': c})

def get_content_group_obj(request, gtype, gname):
    cg = ContentGroup.by_name(gtype, gname)
    return cg

@cache(settings.CACHE_LONG, "general_content_article")
def get_article_old_website(request):
    try:
        id = request.GET.get("ref")
        a = Article.objects.get(pk=id)
        return HttpResponse(a._render("page",request=request))
    except:
        raise Http404

# sure looks cacheworthy
@cache(settings.CACHE_STANDARD, "helper")
def filter_helper(qs, section_str, type_str, url_base):
    """Return a dictionary with components of content_list filter interface."""
    
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

@cache(settings.CACHE_SHORT, "general_generated_toparticles")
def top_articles(section, dt=None):
    """Return prioritized articles from @section"""
    if isinstance(section, basestring):
        key = 'section__name'
    else:
        key = 'section'
    stories = Article.objects.prioritized().filter(**{key: section})
    
    if(dt is not None):
        stories = stories.filter(issue__issue_date__lte=dt)
    return stories

def rotatables(section=None, limit=4):
    """Return the rotatable content for a section (or the front)."""
    c = Content.objects.prioritized()
    if section is not None:
        c = c.filter(section=section)
    #For some reason, Q(rotatable=2) | Q(rotatable=3) doesn't work.
    # It probably has something to do with .extra() in .prioritized()
    b = list(c.filter(rotatable=2)[:limit]) #stuff on front and sections
    if len(b) == limit:
        return b
    r = 3 if section is None else 1
    return (b + list(c.filter(rotatable=r))[:limit])[:limit]

def last_month():
    return date.today() + timedelta(days=-30)

def last_year():
    return date.today() + timedelta(days=-365)
