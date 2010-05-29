import sys
import re
from StringIO import StringIO
from datetime import datetime, timedelta, date

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.urlresolvers import resolve
from django.db import connection
from django.db.models import Count, Max, Q, Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response
from django.template import Context, loader, TemplateDoesNotExist
from django.utils import simplejson
from django.views.decorators.cache import cache_page

from crimsononline.content.forms import ContactForm, FlybyTipForm
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from crimsononline.common.caching import funcache as cache
from crimsononline.common.utils.paginate import paginate
from crimsononline.common.utils.strings import strip_commas
from crimsononline.common.utils.lists import first_or_none
from crimsononline.common.forms import DateSelectWidget
from crimsononline.common.templatetags.common import human_list

# ============ ACTUAL VIEWS =====================

@cache(settings.CACHE_STANDARD, "sitemap")
def sitemap(request, year=None, issue=None):
    if year is None:
        oldest = Article.objects.order_by("issue__issue_date")[0].issue.issue_date.year
        newest = Article.objects.order_by("-issue__issue_date")[0].issue.issue_date.year
        years = range(newest,oldest-1,-1)
        months = [("%02d"%x) for x in range(1,13)]
        return render_to_response("sitemap/sitemap_base.html",{'years':years})
    elif year is not None and issue is None:
        issues = Issue.objects.filter(issue_date__year=year).order_by("issue_date")
        return render_to_response("sitemap/sitemap_issues.html",{'year':year, 'issues':issues})
    elif issue is not None:
        try:
            issue = Issue.objects.get(pk=issue)
            ars = Article.objects.filter(issue=issue)
            return render_to_response("sitemap/sitemap_articles.html",{'articles': ars,'issue':issue})
        except:
            return Http404

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
        except:
            # TODO: remove this 404, just say issue not found
            raise Http404

    sportsblog = ContentGroup.objects.get(name='The Back Page')
    
    # This is necessary because just exclude(group=sportsblog) will also exclude NULL entries,
    # i.e. ungrouped content.  This is because of how mysql handles NULL.  The Django ORM
    # should really solve this problem automatically, but that's another story.
    stories = (top_articles('News, Sports', dt)
                  .filter(~Q(group=sportsblog) | Q(group__isnull=True)))

    dict = {}
    dict['rotate'] = rotatables(None, 4)

    #dict['past_issues'] = DateSelectWidget().render(name="past_issues",
    #                                                value=[m, d, y])
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    more_stories = []
    for story in stories[4:]:
        if story.section != Section.objects.get(name='Sports'):
            more_stories.append(story)
        if len(more_stories) == 9:
            break
    dict['more_stories'] = more_stories
    dict['opeds'] = top_articles('Opinion', dt)[:4]
    dict['arts'] = top_articles('Arts', dt)[:4]
    # Prevent sports articles that showed up in top articles from appearing again
    dict['sports'] = [x 
                      for x
                      in (top_articles('Sports', dt).filter(~Q(group=sportsblog) | Q(group__isnull=True)))[:10]
                      if x not in dict['top_stories']][:4]
    dict['fms'] = top_articles('FM', dt)[:4]
    #dict['issue'] = Issue.get_current()
    dict['galleries'] = Gallery.objects.prioritized(40)[:6]
    dict['videos'] = YouTubeVideo.objects.prioritized(60)[:3]

    return render_to_response('index.html', dict)

REMOVE_P_RE = re.compile(r'page/\d+/$')
@cache_page(settings.CACHE_LONG)
def writer(request, pk, f_name, m_name, l_name, page=1, sections=None, types=None):
    """Show the view for a specific writer."""

    url_base = "/writer/%s/%s_%s_%s" % (pk, f_name, m_name, l_name)
    w = get_object_or_404(Contributor, pk=pk)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_name, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
    f = filter_helper(request,
        w.content.all().order_by('-issue__issue_date'),
        sections, types, w.get_absolute_url()
    )

    w.number_of_articles = Article.objects.filter(contributors=w).count()
    d = paginate(f.pop('content'), page, 10)
    d.update({'page': page, 'url_base': url_base})
    w.last_update = Content.objects.filter(contributors=w).aggregate(Max('issue__issue_date'))['issue__issue_date__max']
    d.update({'writer': w, 'url': REMOVE_P_RE.sub(request.path, '')})
    d.update(f)

    t = 'writer.html'
    if request.GET.has_key('ajax'):
        data = {'content_list': render_to_string('ajax/content_list_page.html', d),
            'content_filters': render_to_string('ajax/content_list_filters.html', d)}
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')

    return render_to_response(t, d)

@cache_page(settings.CACHE_LONG)
def tag(request, tag, page=1, sections=None, types=None):
    """The view for a specific tag."""

    url_base = "/tag/%s" % (tag)

    tag = get_object_or_404(Tag, text=tag.replace('_', ' '))
    if not types or types.find("image") == -1:
        content = Content.objects.recent.filter(tags=tag).exclude(content_type__name='image')
    else:
        content = Content.objects.recent.filter(tags=tag)

    f = filter_helper(request, content, sections, types,
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

    writers = get_tag_top_contribs(tag.pk)
    reltags = get_related_tags(tag.pk)

    d = paginate(f.pop('content'), page, 10)
    d.update({'page': page, 'url_base': url_base})
    d.update({'tag': tag, 'url': tag.get_absolute_url(), 'tags': reltags,
        'featured': featured_articles, 'top_contributors': writers,})
    d.update(f)

    t = 'tag.html'
    if request.GET.has_key('ajax'):
        data = {'content_list': render_to_string('ajax/content_list_page.html', d),
            'content_filters': render_to_string('ajax/content_list_filters.html', d)}
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')
    return render_to_response(t, d)

@cache(settings.CACHE_LONG)
def get_tag_top_contribs(pk):
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
            content.id NOT IN (SELECT content_ptr_id FROM content_image) AND
            content_tags.tag_id = %i AND
            content.pub_status = 1
        GROUP BY content_contributors.contributor_id
        ORDER BY objcount DESC
        LIMIT 5
    """ % pk) # TODO: should actually do this with sqlite3 replacement, not python
    rows = [r for r in cursor.fetchall() if r[1] > 0]
    writers = Contributor.objects.filter(pk__in=[r[0] for r in rows])
    contrib_count = dict(rows)
    for w in writers:
        w.c_count = contrib_count[w.pk]
        w.rece = w.content.recent[:1][0].issue.issue_date
    writers = list(writers)
    writers.sort(lambda x, y: cmp(y.c_count, x.c_count))
    return writers

@cache(settings.CACHE_LONG)
def get_related_tags(pk):
    # related tags (tags with most shared content)
    #  select the tags for which there are the most objects that have both
    #  this tag and that tag within some timeframe
    cursor = connection.cursor()
    cursor.execute("""SELECT cgt2.tag_id,
        count(cgt2.content_id) AS o_count
        FROM content_content_tags AS cgt1
        JOIN content_content_tags AS cgt2
        ON cgt1.content_id=cgt2.content_id
        WHERE cgt1.tag_id = %(pk)i AND cgt2.tag_id != %(pk)i
        GROUP BY cgt2.tag_id ORDER BY o_count DESC LIMIT 15;""" % {'pk': pk}
    )
    rows = cursor.fetchall()
    tags = Tag.objects.filter(pk__in=[r[0] for r in rows])
    tags_count = dict(rows)
    for t in tags:
        t.content_count = tags_count[t.pk]
    tags = list(tags)
    tags.sort(lambda x,y: cmp(y.content_count, x.content_count))
    return tags

# ============= Section Views ============

@cache_page(settings.CACHE_SHORT)
def section_news(request):
    """Show the view for the news section page."""

    nav = 'news'
    section = Section.cached(nav)
    stories = top_articles(section)[:22]
    rotate = rotatables(section, 4)

    series = ContentGroup.objects.filter(section=section) \
        .annotate(c_count=Count('content')).filter(c_count__gte=3) \
        .annotate(latest=Max('content__issue__issue_date')) \
        .order_by('-latest')[:2]

    today = datetime.today()
    lastweek = today-timedelta(7)
    lastmonth = today-timedelta(120)

    featured = Article.objects.filter(section=section) \
        .filter(issue__issue_date__gte=lastmonth) \
        .filter(issue__issue_date__lte=lastweek) \
        .order_by('-priority')[:3]

    return render_to_response('sections/news.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_opinion(request):
    """Show the view for the opinion section page."""

    nav = 'opinion'
    section = Section.cached(nav)
    stories = top_articles(section)[:12]
    rotate = rotatables(section, 4)
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date')).order_by('-recent')

    today = datetime.today()
    lastweek = today-timedelta(7)
    lastmonth = today-timedelta(30)

    featured = Article.objects.filter(section=section) \
        .filter(issue__issue_date__gte=lastmonth) \
        .filter(issue__issue_date__lte=lastweek) \
        .order_by('-priority')[:3]

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
        scrutiny = stories.filter(tags__text='Scrutiny')[0]
    except IndexError:
        scrutiny = None
    try:
        endpaper = stories.filter(tags__text='Endpaper')[0]
    except IndexError:
        endpaper = None
    rotate = rotatables(section, 15)
    itm = stories.filter(tags__text='In The Meantime')[:3]
    ftm = stories.filter(tags__text='For The Moment')[:9]
    issues = Issue.objects.exclude(Q(fm_name=None)|Q(fm_name=''))[:3]
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))

    today = datetime.today()
    lastweek = today-timedelta(7)
    lastmonth = today-timedelta(30)

    featured = Article.objects.filter(section=section) \
        .filter(issue__issue_date__gte=lastmonth) \
        .filter(issue__issue_date__lte=lastweek) \
        .order_by('-priority')[:3]

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
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date'))
    reviews = {}
    #for t in ['movie', 'music', 'book']:
    #    reviews[t] = Review.objects.filter(type=t)[:4]

    today = datetime.today()
    lastweek = today-timedelta(7)
    lastmonth = today-timedelta(30)

    featured = Article.objects.filter(section=section) \
        .filter(issue__issue_date__gte=lastmonth) \
        .filter(issue__issue_date__lte=lastweek) \
        .order_by('-priority')[:4]

    return render_to_response('sections/arts.html', locals())

@cache_page(settings.CACHE_SHORT)
def section_media(request):
    """Show the view for the media section page."""

    if request.method == 'GET':
        page = request.GET.get('page', 1)
    else:
        raise Http404
    nav = 'media'

    sort = request.GET.get('sort')
    if sort == 'read':
        RECENT_DAYS = timedelta(days=60)
        newer_than = datetime.now() - RECENT_DAYS
        content = Content.objects \
                         .filter(issue__issue_date__gte=newer_than) \
                         .annotate(hits=Sum('contenthits__hits')) \
                         .order_by('-hits')
    else:
        content = Content.objects.recent

    c_type = request.GET.get('type')
    if c_type == 'gallery':
        cts = [Gallery.ct()]
    elif c_type == 'you tube video':
        cts = [YouTubeVideo.ct()]
    else:
        cts = [YouTubeVideo.ct(), Gallery.ct()]
    content = content.filter(content_type__in=cts)

    section = request.GET.get('section')
    if section and request.GET.has_key('ajax'):
        try:
            s_obj = Section.objects.get(name__iexact=section)
            content = content.filter(section=s_obj)
        except:
            pass

    d = paginate(content, page, 6)
    d.update({'nav': nav})

    t = 'sections/media.html'
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
    sportsblog = ContentGroup.objects.get(name='The Back Page')
    section = Section.cached(nav)
    # See index() for an explanation of this filter
    stories = top_articles(section).filter(~Q(group=sportsblog) | Q(group__isnull=True))
    rotate = rotatables(section)
    latest = (Article.objects.filter(section=section).order_by('-modified_on')
                 .filter(~Q(group=sportsblog) | Q(group__isnull=True)))
    latest = latest[:10]
    blog = stories.filter(group__type='blog')
    athlete = first_or_none(stories.filter(tags__text='athlete of the week'))
    stories = stories[:4]
    scores = Score.objects.order_by('-event_date')[:10]
    sports = Tag.objects.filter(category='sports').order_by('text')
    video = first_or_none(YouTubeVideo.objects.recent.filter(section=section))
    columns = ContentGroup.objects.filter(section=section, active=True,
        type='column').annotate(recent=Max('content__issue__issue_date')).order_by('-recent')
    columns = columns[:3]

    try:
        srcm = ContentModule.objects.get(name="sports.rotator")
        if srcm.expiration < datetime.now():
            featured = []
        else:
            featured_group_name = ContentModule.objects.get(name="sports.rotator").comment
            featured_group_name.strip()
            featured_group = ContentGroup.objects.filter(section=section, active=True,
                name=featured_group_name)
            featured = Article.objects.filter(section=section, group=featured_group)
    except:
        featured = []

    return render_to_response('sections/sports.html', locals())

FLYBY_RESULTS_PER_PAGE = 7
@cache_page(60*20)
def section_flyby(request, page=1, tags='', cg=None):
    nav = 'flyby'
    section = Section.cached(nav)

    content = Article.objects.recent.filter(section=section)
    if cg:
        content = content.filter(group=cg)
        tag = ''
    # It says "tags," but we're only going to support one at a time
    # Elif used because we don't want to allow filtering by both tags and a cg
    elif tags:
        try:
            tag = Tag.objects.get(text=tags)
        except Tag.DoesNotExist:
            tag = ''
        if tag:
            content = content.filter(tags=tag)
            tag = str(tag)
    else:
        tag = ''
    quotetag = Tag.objects.get(text='Flyby Quote')
    # I don't think it's likely that we'll ever have a meaningful distinction of blog/series/column WITHIN flyby,
    # but should it become necessary that can be filtered below
    series = list(ContentGroup.objects.filter(active=True).filter(section=section))
    featured = rotatables(section, 6)
    video = first_or_none(YouTubeVideo.objects.recent.filter(section=section))
    paginator = Paginator(content, FLYBY_RESULTS_PER_PAGE)
    url_base = "/section/flyby/"
    # Jesus, Andy.
    try:
        entries = paginator.page(page)
    except:
        entries = paginator.page(1)
    return render_to_response('flyby/content_list.html', locals())

def flyby_tip(request):
    if request.method == 'POST':
        form = FlybyTipForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            recipients = [settings.FLYBY_TIP_ADDRESS]
            message = 'Tip submitted on Flyby:\n\n%s' % (message)
            send_mail('Flyby tip submitted', message, 'flybybot@thecrimson.com', recipients, fail_silently=True)
            return HttpResponse('Worked')
    return HttpResponse('Failed')
    
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
    """View for displaying a piece of content on a page
    Validates the entire URL
    """
    try:
        c = get_content_obj(request, ctype, year, month, day,
                            slug, content_group)
    except Content.DoesNotExist:
        raise Http404
    # redirect to canonical URL
    if request.path != c.get_absolute_url():
        return HttpResponseRedirect(c.get_absolute_url())
    if request.method == 'GET':
        return HttpResponse(c._render(request.GET.get('render','page'),
                            request=request))
    raise Http404

# no need to cache these two i don't think, since they all go through get_content in the end
def get_content_obj(request, ctype, year, month, day, slug, content_group=None):
    """Retrieve a content object from the database (no validation of params)"""
    ctype = ctype.replace('-', ' ') # convert from url
    try:
        return Content.objects.get(issue__issue_date=date(int(year), int(month), int(day)),
                                   slug=slug)
    except ValueError:
        raise Content.DoesNotExist

def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug):
    """View for displaying a piece of grouped content on a page
    Validates the entire url
    """
    # validate the contentgroup
    cg = get_grouped_content_obj(request, gtype, gname, ctype,
        year, month, day, slug)
    if cg:
        return get_content(request, ctype, year, month, day, slug, cg)
    raise Http404

def get_grouped_content_obj(request, gtype, gname, ctype, year, month, day, slug):
    #TODO: i don't think this function is right at all
    return ContentGroup.by_name(gtype, gname)

@cache(settings.CACHE_STANDARD, "general_contentgroup")
def get_content_group(request, gtype, gname, page=1, tags=None):
    """Render a Content Group."""
    # validate the contentgroup
    cg = get_content_group_obj(request, gtype, gname)
    if not cg:
        raise Http404
    c = cg.content.all()
    # check if flyby content group - if so, just pass to flyby view
    if cg.section == Section.objects.get(name='flyby'):
        return section_flyby(request, page, cg=cg)
    if tags:
        taglist = tags.split(',')
        tagobjlist = []
        for tag in taglist:
            try:
                tag = Tag.objects.get(text=tag)
                if tag not in tagobjlist:
                    tagobjlist.append(tag)
            except Tag.DoesNotExist:
                pass
        c = c.filter(tags__in=tagobjlist).distinct()
    c = c.order_by('-issue__issue_date', '-modified_on')
    d = paginate(c, page, 5)
    d['cg'] = cg
    d['url_base'] = "/%s/%s" % (gtype, gname)
    # Eventually this should go through filter_helper, but it sucks too much right now
    if tags:
        d['tag_str'] = '/tags/' + ','.join([tag.text for tag in tagobjlist])
    else:
        d['tag_str'] = ''
    if cg.section:
        d['nav'] = cg.section.name.lower()
    # d['content'] = c
    try:
        loader.get_template('contentgroup/%s/%s/content_list.html' % (gtype, gname))
        t = 'contentgroup/%s/%s/content_list.html' % (gtype, gname)
    except TemplateDoesNotExist:
        t = "contentgroup.html"
    return render_to_response(t, d)

def get_content_group_obj(request, gtype, gname):
    return ContentGroup.by_name(gtype, gname)

# sure looks cacheworthy
#@cache(settings.CACHE_STANDARD, "helper")
def filter_helper(req, qs, section_str, type_str, url_base):
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
        show_filter_1 = True
    else:
        section_str = [s.name.lower() for s in Section.all()]
        sections = Section.all()
        show_filter_1 = False
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

    # models to show in the filter interface... so ghetto
    content_choices = ["article", "image"]
    if type_str:
        type_str = type_str.replace('-', ' ') # convert from url
        type_str = [t.lower() for t in type_str.split(',') if t in content_choices + ["other"]]

        if "other" in type_str:
            othertypes = [t for t in Content.types() if t.name not in [a.lower() for a in content_choices]]
        else:
            othertypes = []

        # Models to show
        filter_types = [t for t in Content.types() if t.name.lower() in type_str] + othertypes
        types = type_str
        content = content.filter(content_type__in=filter_types)
        show_filter_2 = True
    # all content types
    else:
        types = content_choices + ["other"]
        show_filter_2 = False

    # Iterate over list choices and form URLs
    for type in content_choices + ["other"]:
        sel = type in types

        t_str = ','.join([t for t in (types + [type]) if t != type or t not in types])

        url = url_base
        url += ('sections/%s/' % o_section_str if o_section_str else '')
        url += ('types/%s/' % t_str if t_str else '')

        if type != "other":
            curtype = [t for t in Content.types() if t.name.lower() == type][0]
            ct = len(unfilteredcontent.filter(content_type=curtype))
        else:
            othertypes = [t for t in Content.types() if t.name not in [a.lower() for a in content_choices]]
            ct = len(unfilteredcontent.filter(content_type__in=othertypes))

        if(type in content_choices + ["other"]):
            tps[type[0].upper() + type[1:]] = {'selected': sel, 'url': url, 'count':ct}

    sect_str = "/sections/" + ",".join(section_str) if len(sections) != Section.all().count() else ""
    typ_str = "/types/" + ",".join(types) if len(content_choices) + 1 != len(types) else ""

    return {'content': content, 'sections': sects,'section_str':sect_str, 'types': tps, 'type_str': typ_str,'show_filter':(show_filter_1 or show_filter_2)}

def top_articles(section, dt=None):
    """Return a queryset of prioritized articles from @section"""
    qexp = []
    # Check if section is a comma-delimited list of sections
    if isinstance(section, basestring) and section.count(',') > 0:
        section = [x.strip() for x in section.split(',')]
    # Process section, be it a list, string, or Section object, into Q object(s)
    if isinstance(section, list):
        for sec in section:
            if isinstance(sec, basestring):
                qexp.append(Q(**{'section__name': sec}))
            else:
                qexp.append(Q(**{'section': sec}))
    elif isinstance(section, basestring):
        qexp = [Q(**{'section__name': section})]
    else:
        qexp = [Q(**{'section': section})]
    # We want to OR all the Qexps together
    qexp = reduce(lambda x, y: x | y, qexp) if len(qexp) > 1 else qexp[0]
    stories = []
    #for x in range(0, 5):
    #    stories = Article.objects.prioritized(20 + 40 * x).filter(qexp)
    #    if len(stories) > 0:
    #        break
    stories = Article.objects.prioritized(50).filter(qexp)
    if(dt is not None):
        stories = stories.filter(issue__issue_date__lte=dt)
    return stories

def rotatables(section=None, limit=4):
    """Return the rotatable content for a section (or the front)."""
    c = Content.objects.prioritized()
    if section is None:
        b = list(c.filter(Q(rotatable=2) | Q(rotatable=3))[:limit])
    else:
        c = c.filter(section=section)
        b = list(c.filter(Q(rotatable=2) | Q(rotatable=1))[:limit])
    if len(b) == 0:
        c = Content.objects.recent
        if section is None:
            b = list(c.filter(Q(rotatable=2) | Q(rotatable=3))[:limit])
        else:
            c = c.filter(section=section)
            b = list(c.filter(Q(rotatable=2) | Q(rotatable=1))[:limit])
    return b

def last_month():
    return date.today() + timedelta(days=-30)

def last_year():
    return date.today() + timedelta(days=-365)

#View for the contact page
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)

        if form.is_valid():
            message_type = form.cleaned_data["message_type"]
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            to_email = form.cleaned_data['to_email']
            message = form.cleaned_data['message']
            recipients = [to_email]

            message = 'Message sent from %s (%s):\n\n%s' % (name, email, message)

            send_mail('Message submitted on www.thecrimson.com', message, email,
            recipients, fail_silently=True)

            return render_to_response('contact/thanks.html')
    else:
        m_type = request.GET.get('message_type','')
        form = ContactForm(initial={'message_type': m_type})

    return render_to_response('contact/contact.html', {'form': form})
    
# commencement
def commencement2010(request):
    nav = 'news'
    section = Section.cached(nav)
    ctag = Tag.objects.get(text='Commencement 2010')
    topstories = Article.objects.prioritized(30).filter(tags=ctag)
    galleries = Gallery.objects.filter(tags=ctag)[:6]
    
    return render_to_response('special/commencement2010/main.html', locals())
    
def commencement2010_1960(request):
    nav = 'news'
    section = Section.cached(nav)
    edsec = Section.objects.get(name='Opinion')
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Class of 1960')
    ptag = Tag.objects.get(text='Profiles')
    profiles = Article.objects.filter(tags=ctag).filter(tags=stag).filter(tags=ptag)
    ed = Article.objects.filter(tags=ctag).filter(tags=stag).filter(section=edsec)
    allstories = [x for x in Article.objects.prioritized(30).filter(tags=ctag).filter(tags=stag) if x not in profiles and x not in ed]
    features = allstories[:4]
    stories = allstories[4:8]
    rotated = Content.objects.filter(tags=ctag).filter(tags=stag).filter(Q(rotatable=2) | Q(rotatable=1))[:6]

    return render_to_response('special/commencement2010/1960.html', locals())
    
def commencement2010_1985(request):
    nav = 'news'
    section = Section.cached(nav)
    edsec = Section.objects.get(name='Opinion')
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Class of 1985')
    ptag = Tag.objects.get(text='Profiles')
    profiles = Article.objects.filter(tags=ctag).filter(tags=stag).filter(tags=ptag)
    ed = Article.objects.filter(tags=ctag).filter(tags=stag).filter(section=edsec)
    allstories = [x for x in Article.objects.prioritized(30).filter(tags=ctag).filter(tags=stag) if x not in profiles and x not in ed]
    features = allstories[:3]
    stories = allstories[3:10]
    rotated = Content.objects.filter(tags=ctag).filter(tags=stag).filter(Q(rotatable=2) | Q(rotatable=1))[:6]
   
    return render_to_response('special/commencement2010/1985.html', locals())
    
def commencement2010_yir(request):
    nav = 'news'
    section = Section.cached(nav)
    edsec = Section.objects.get(name='Opinion')
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Year in Review')
    covtaglist = ['College', 'On Campus', 'Faculty', 'Cambridge', 'University']
    covtaglist = [Tag.objects.get(text=x) for x in covtaglist]
    features = Article.objects.prioritized(30).filter(tags=ctag).filter(tags=stag)[:7]
    ed = Article.objects.filter(tags=ctag).filter(tags=stag).filter(section=edsec)
    sectionarticles = [[y for y in Article.objects.filter(tags=ctag).filter(tags=stag).filter(tags=x) if y not in features][:7] for x in covtaglist]
    rotated = Content.objects.filter(tags=ctag).filter(tags=stag).filter(Q(rotatable=2) | Q(rotatable=1))[:6]
    
    return render_to_response('special/commencement2010/yir.html', locals())
    
def commencement2010_sports(request):
    nav = 'sports'
    section = Section.cached(nav)
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Year in Sports')
    # team of year + runnerups
    teamofyear = Article.objects.filter(tags=stag).filter(headline__startswith='TEAM OF THE YEAR:')
    teamofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='TEAM OF THE YEAR RUNNER-UP:')
    # male rookie + runnerup
    mrofyear = Article.objects.filter(tags=stag).filter(headline__startswith='MALE ROOKIE OF THE YEAR:')
    mrofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='MALE ROOKIE OF THE YEAR RUNNER-UP:')
    # male rookie + runnerup
    frofyear = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE ROOKIE OF THE YEAR:')
    frofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE ROOKIE OF THE YEAR RUNNER-UP:')
    # game of year + runnerup
    gofyear = Article.objects.filter(tags=stag).filter(headline__startswith='GAME OF THE YEAR:')
    gofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='GAME OF THE YEAR RUNNER-UP:')
    # coach of year + runnerup
    cofyear = Article.objects.filter(tags=stag).filter(headline__startswith='COACH OF THE YEAR:')
    cofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='COACH OF THE YEAR RUNNER-UP:')
    # comeback athlete + runnerup
    caofyear = Article.objects.filter(tags=stag).filter(headline__startswith='COMEBACK ATHLETE OF THE YEAR:')
    caofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='COMEBACK ATHLETE OF THE YEAR RUNNER-UP:')
    # male athlete of year + runnersup
    maofyear = Article.objects.filter(tags=stag).filter(headline__startswith='MALE ATHLETE OF THE YEAR:')
    maofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='MALE ATHLETE OF THE YEAR RUNNER-UP:')
    # female ___
    faofyear = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE ATHLETE/ROOKIE OF THE YEAR:')
    faofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE ATHLETE OF THE YEAR RUNNER-UP:')
    # male breakout
    mbaofyear = Article.objects.filter(tags=stag).filter(headline__startswith='MALE BREAKOUT ATHLETE OF THE YEAR:')
    mbaofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='MALE BREAKOUT ATHLETE OF THE YEAR RUNNER-UP:')
    # female breakout
    fbaofyear = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE BREAKOUT ATHLETE OF THE YEAR:')
    fbaofyearru = Article.objects.filter(tags=stag).filter(headline__startswith='FEMALE BREAKOUT ATHLETE OF THE YEAR RUNNER-UP:')
    # season recaps
    sportstags = Tag.objects.filter(category='sports').exclude(text='Year in Sports')
    recaps = Article.objects.filter(tags=stag).filter(headline__startswith='SEASON RECAP:')
    arecaps = []
    for x in recaps:
        arecaps.append([x, [y for y in x.tags.all() if y in sportstags][0].text])
    arecaps.sort(key=lambda x: x[1])
    # parting shots
    partingshots = Article.objects.filter(tags=stag).filter(headline__startswith='PARTING SHOT:')
    
    return render_to_response('special/commencement2010/sports.html', locals())
    
def commencement2010_seniors(request):
    nav = 'news'
    section = Section.cached(nav)
    flyby = Section.cached('flyby')
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Seniors')
    wtag = Tag.objects.get(text='Weddings')
    stories = Article.objects.prioritized(30).filter(tags=ctag).filter(tags=stag).exclude(tags=wtag).exclude(section=flyby)[:5]
    rotated = Content.objects.filter(tags=ctag).filter(tags=stag).filter(Q(rotatable=2) | Q(rotatable=1))[:10]
    weddings = Article.objects.filter(tags=ctag).filter(tags=stag).filter(tags=wtag)
    wthird = len(weddings) / 3 + (1 if len(weddings) % 3 == 2 else 0)
    weddings = [weddings[0:wthird], weddings[wthird:wthird * 2], weddings[wthird * 2:]]
    weddings.sort(key=lambda x: len(x), reverse=True)
    
    return render_to_response('special/commencement2010/senior.html', locals())
    
def commencement2010_pov(request):
    nav = 'opinion'
    section = Section.cached(nav)
    ctag = Tag.objects.get(text='Commencement 2010')
    stag = Tag.objects.get(text='Parting Shot')
    ntag1 = Tag.objects.get(text='Year in Review')
    ntag2 = Tag.objects.get(text='Class of 1960')
    ntag3 = Tag.objects.get(text='Class of 1985')
    
    partingshots = Article.objects.filter(tags=ctag).filter(tags=stag).exclude(tags=ntag1).exclude(tags=ntag2).exclude(tags=ntag3)
    rotated = Content.objects.filter(tags=ctag).filter(section=section).filter(Q(rotatable=2) | Q(rotatable=1))[:6]
    opeds = Article.objects.filter(tags=ctag).filter(section=section).exclude(tags=ntag1).exclude(tags=ntag2).exclude(tags=ntag3)
    opeds = [x for x in opeds if x not in partingshots]
    wthird = len(opeds) / 3 + (1 if len(opeds) % 3 == 2 else 0)
    opeds = [opeds[0:wthird], opeds[wthird:wthird * 2], opeds[wthird * 2:]]
    opeds.sort(key=lambda x: len(x), reverse=True)
    pthird = (len(partingshots) - 4) / 3 + (1 if (len(partingshots) - 4) % 3 == 2 else 0)
    partingshots = [partingshots[:pthird + 4], partingshots[pthird + 4:pthird * 2 + 4],
                    partingshots[pthird * 2 + 4:]]
    
    return render_to_response('special/commencement2010/pov.html', locals())