from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
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
    return render_to_response('writer.html', {'writer': w, 'articles': articles})

def section(request, section):
    #TODO: validate section
    dict = {}
    dict['nav'] = section.lower()
    dict['issue'] = Issue.get_current()
    dict['articles'] = Article.objects \
        .filter(issue=dict['issue'].id) \
        .filter(section__name__iexact=section)
    dict['title'] = section.capitalize()
    return render_to_response('section.html', dict)
    
    
# =========== view helpers ============== #
def get_top_articles(issue_id, section, limit=10):
    """returns the top limit articles from section for the issue"""
    
    return Article.objects.filter(issue__id__exact=issue_id,
                                    section__name__exact=section) \
                            .order_by('-priority')[:limit]