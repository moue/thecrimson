from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from crimsononline.subscriptions.forms import EmailSubscriptionForm
from crimsononline.content.models import Tag, Contributor
from crimsononline.common.forms import fbmc_search_helper


def email_confirm(request):
    if request.method == 'POST' or \
        (request.method == 'GET' and request.GET.get('')):
        f = EmailConfirmSubscriptionForm(request.POST)
        if f.is_valid():
            pass


def email_signup(request):
    if request.method == 'POST':
        # process a submitted form
        f = EmailSubscriptionForm(request.POST)
        if f.is_valid():
            f.save()
            url = '/subscribe/email/confirm/?email=%s' % f.cleaned_data['email']
            return HttpResponseRedirect(url)
    if request.method == 'GET':
        tags = request.GET.get('tags', None)
        contributors = request.GET.get('contributors', None)
        sections = request.GET.get('sections', None)
        try:
            tags = [int(t) for t in tags.split(',') if t]
        except:
            tags = None
        try:
            contributors = [int(c) for c in contributors.split(',') if c]
        except:
            contributors = None
        try:
            sections = [int(s) for s in sections.split(',') if c]
        except:
            sections = None
        f = EmailSubscriptionForm(initial={'tags': tags, 
            'contributors': contributors, 'sections': sections})
    return render_to_response('email/signup.html', {'form': f})
    

def fbmc_search(request, type):
    """
    Returns a text response for FBModelChoice Field
    """
    q_str, excludes, limit = fbmc_search_helper(request)
    if type == 'tag':
        objs = Tag.objects.filter(text__contains=q_str)
    else:
        objs = Contributor.objects.filter(
            Q(first_name__contains=q_str) | Q(last_name__contains=q_str),
            is_active=True)
    objs = objs.exclude(pk__in=excludes).order_by('-pk')[:limit]
    return render_to_response('fbmc_result_list.txt', {'objs': objs})