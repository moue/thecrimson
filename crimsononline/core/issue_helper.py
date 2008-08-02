from django.core.cache import cache
from crimsononline.core.models import Issue

def current_issue():
    """gets current issue from cache"""
    i = cache.get('current_issue')
    if not i:
        i = Issue.objects.latest('issue_date')
        set_issue(i)
    return i
    
def set_issue(issue, timeout=100000):
    return cache.set('current_issue', issue, timeout)