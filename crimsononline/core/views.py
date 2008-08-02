from django.shortcuts import render_to_response, get_object_or_404
from crimsononline.core.models import *
from crimsononline.core.issue_helper import current_issue

def index(request):
    nav = 'index'
    
    #TODO: change this to assign to current issue (app wide setting)
    issue = Issue.objects.filter(id__exact=1)[0]
    
    stories = get_top_articles(issue.id, 'News')
    top_stories = stories[:3]
    more_stories = stories[3:9]
    opeds = get_top_articles(issue.id, 'Ed')[:6]
    
    return render_to_response('index.html', {'nav': nav,
                                            'top_stories': top_stories, 
                                            'more_stories': more_stories,
                                            'opeds': opeds, 
                                            'issue': issue})
    
def article(request, article_id):
    a = get_object_or_404(Article, pk=article_id)
    nav = a.section.name.lower()
    return render_to_response('article.html', {'article': a, 'nav': nav})
    
def writer(request, contributor_id):
    w = get_object_or_404(Contributor, pk=contributor_id)
    articles = w.article_set.all()
    return render_to_response('writer.html', {'writer': w, 'articles': articles})
    
def daily_news(request, issue_id=current_issue()):
    return render_to_response('news.html', {})
    
# =========== view helpers ============== #
def get_top_articles(issue_id, section):
    """returns the top limit articles from section for the issue"""
    
    return Article.objects.filter(issue__id__exact=issue_id,
                                    section__name__exact=section) \
                            .order_by('-priority')