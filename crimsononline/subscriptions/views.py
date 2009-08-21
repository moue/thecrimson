from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth import *
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login as d_login, logout as d_logout
from django.shortcuts import render_to_response

from crimsononline.subscriptions.forms import \
    EmailSubscribeForm, EmailSubscribeConfirmForm, EmailSubscriptionManageForm
from crimsononline.content.models import Tag, Contributor
from crimsononline.subscriptions.models import EmailSubscription
from crimsononline.common.forms import fbmc_search_helper

def email_confirm(request):
    """Confirm an email subscription.
    
    GET requests with a subscription id and passcode for an active
    subscription shows a success page; inactive subscriptions get confirmed,
    via a javascript POST submission.
    POST requests validate confirmation and confirm.
    """
    context = {}
    if request.method == 'GET':
        try:
            pk = int(request.GET['subscription_id'])
            passcode = request.GET['passcode']
            s = EmailSubscription.objects.get(pk=pk, passcode=passcode)
        except (KeyError, ValueError, EmailSubscription.DoesNotExist):
            raise Http404
        if s.is_active:
            context['success'] = True
        else:
            f = EmailSubscribeConfirmForm({'subscription_id': pk, 
                'passcode': passcode})
            context['form'] = f
            context['submit'] = True
    elif request.method == 'POST':
        f =EmailSubscribeConfirmForm(request.POST)
        if f.is_valid():
            s = f.cleaned_data['email_subscription']
            s.is_active = True
            s.save()
            context['success'] = True
        else:
            context['error'] = True
    else:
        raise Http404
    return render_to_response('email/confirm.html', context)

def email_manage(request):
    if request.method == 'POST' or request.method == 'GET':
        d = getattr(request, request.method)
        pk = int(d.get('id', 0))
        passcode = d.get('passcode', '')
        try:
            s = EmailSubscription.objects.get(pk=pk, passcode=passcode)
        except:
            return render_to_response('email/manage.html', {'fail': True})
        
        if request.method == 'POST':
            f = EmailSubscriptionManageForm(request.POST, instance=s)
            if f.is_valid():
                f.save()
                success = True
        else: # request.method == 'GET'
            f = EmailSubscriptionManageForm(instance=s)
            success = False
        return render_to_response('email/manage.html', 
                                  {'form': f, 'success': success})
    else:
        raise Http404

def email_signup(request):
    if request.method == 'POST':
        # process a submitted form
        f = EmailSubscribeForm(request.POST)
        if f.is_valid():
            f.save()
            return render_to_response('email/signup.html', 
                {'success': 1, 'email': f.cleaned_data['email']})
    else:
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
        f = EmailSubscribeForm(initial={'tags': tags, 
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