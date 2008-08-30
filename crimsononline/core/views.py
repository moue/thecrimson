from datetime import datetime, timedelta
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse
from django.template import Context, loader
from django.contrib.flatpages.models import FlatPage
from crimsononline.core.models import *

def index(request):
    issue = Issue.get_current()
    stories = get_top_articles(issue.id, 'News')
    
    dict = {}
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = get_top_articles(issue.id, 'Opinion', 6)
    dict['arts'] = get_top_articles(issue.id, 'Arts', 6)
    dict['sports'] = get_top_articles(issue.id, 'Sports', 6)
    dict['fms'] = get_top_articles(issue.id, 'FM', 6)
    dict['issue'] = issue
    
    return render_to_response('index.html', dict)
    
def article(request, article_id):
    a = get_object_or_404(Article, pk=article_id)
    nav = a.section.name.lower()
    return render_to_response('article.html', {'article': a, 'nav': nav})
    
def writer(request, contributor_id):
    w = get_object_or_404(Contributor, pk=contributor_id)
    articles = w.article_set.all()
    return render_to_response('writer.html', 
                            {'writer': w, 'articles': articles})

def section(request, section, issue_id=None):    
    # validate the section (we don't want /section/balls/ to be a valid url)
    section = filter(lambda x: section.lower() == x.name.lower(), Section.all())
    if len(section) == 0:
        raise Http404
    section = section[0]
    
    # grab the correct issue
    if issue_id is None:
        issue = Issue.get_current()
    else:
        issue = get_object_or_404(Issue, pk=issue_id)
    
    dict = {}
    # grab the appropriate content modules (flatpages)
    dict['fps'] = FlatPage.objects.filter(url__istartswith=request.path) \
        .order_by('url')
    dict['nav'] = section.name.lower()
    dict['issue'] = issue
    dict['articles'] = Article.objects \
        .filter(issue=issue.id) \
        .filter(section__pk=section.pk)
    dict['title'] = section.name.capitalize()
    t = loader.select_template([dict['nav']+'.html', 'section.html'])
    return HttpResponse(t.render(Context(dict)))

    
# =========== view helpers ============== #
def get_top_articles(issue_id, section, limit=10):
    """returns the top limit articles from section for the issue"""
    return (
        Article.objects.filter(issue=issue_id, section__name=section) | \
        Article.web_objects \
            .filter(uploaded_on__gte=datetime.now()-timedelta(hours=48))
    ).order_by('-priority')[:limit]