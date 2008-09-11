from datetime import datetime, timedelta
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
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
    
def article(request, year, month, day, slug):
    year, month, day = int(year), int(month), int(day)
    a = get_object_or_404(Article,
        issue__issue_date__year=year, issue__issue_date__month=month,
        issue__issue_date__day=day, slug=slug)
    nav = a.section.name.lower()
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
    section = filter(lambda x: section.lower() == x.name.lower(), Section.all())
    if len(section) == 0:
        raise Http404
    section = section[0]
    
    # grab the correct issue
    if issue_id is None:
        issue = Issue.get_current()
    else:
        issue = get_object_or_404(Issue, pk=issue_id)
    
    articles = Article.objects.filter(issue=issue.id, section__pk=section.pk)
    # filter based on tags
    if tags is not None:
        tags = tags.lower().replace('_',' ').split(',')
        for tag in tags:
            articles = articles.filter(tags__text=tag)
    
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

    
# =========== view helpers ============== #
def get_top_articles(issue_id, section, limit=10):
    """returns the top limit articles from section for the issue"""
    return Article.objects.filter(issue=issue_id, section__name=section) \
        .order_by('-priority')[:limit]