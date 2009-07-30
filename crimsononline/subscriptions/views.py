from django.db.models import Q
from django.http import HttpResponseRedirect
from django.contrib.auth import *
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login as d_login, logout as d_logout
from django.views.generic.simple import direct_to_template
from crimsononline.subscriptions.forms import SubscribeForm, SubscribeManageForm, SubscribeConfirmForm
from crimsononline.content.models import Tag, Contributor
from crimsononline.subscriptions.models import Subscriber
from crimsononline.common.forms import fbmc_search_helper

def confirm(request):
    if request.user and not request.user.is_anonymous():
        return HttpResponseRedirect("../../")
        
    if request.method == 'POST':
        f =SubscribeConfirmForm(request.POST)
        if f.is_valid():
            s = Subscriber.objects.get(email = request.POST.get('email'))
            if s.is_active == True:
                status = "Subscription already active!"
            elif s.confirm(request.POST.get('confirmation_code')):
                status = "Subscription activated successfully!"
            else:
                status = "Activation failed."
            return direct_to_template(request, 'email/confirm.html', {'form': f, \
                    'status':status})        
    else:
        email_address = request.GET.get('email', None)
        confirmation_code = request.GET.get('confirmation_code', None)
        
        f = SubscribeConfirmForm(initial={'email': email_address,
            'confirmation_code': confirmation_code})
    return direct_to_template(request,'email/confirm.html', {'form': f})

def manage(request):
    if request.method == 'POST':
        f = SubscribeManageForm(request.POST)
        if f.is_valid():
            f.save()
    sub = request.user.subscriber
    tags = [t.pk for t in sub.tags.all()]
    contributors = [c.pk for c in sub.contributors.all()]
    sections = [s.pk for s in sub.sections.all()]

    f = SubscribeManageForm(initial={'sub':sub.pk, 'tags':tags, 'contributors':contributors, 'sections':sections})
    return direct_to_template(request, 'email/signup.html', {'form':f})
    
def register(request):
    if request.user and not request.user.is_anonymous():
        return manage(request)

    else:
        if request.method == 'POST':
            # process a submitted form
            f = SubscribeForm(request.POST)
            if f.is_valid():
                f.save()
                url = '/subscribe/confirm/'
                return HttpResponseRedirect(url)
            else:
                print f.errors
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
            f = SubscribeForm(initial={'tags': tags, 
                'contributors': contributors, 'sections': sections})
        return direct_to_template(request,'email/signup.html', {'form': f})

def login(request):
    if request.user and not request.user.is_anonymous():
        return HttpResponseRedirect("../../")

    username = request.POST.get("username",None)
    password = request.POST.get("password",None)
    
    # modified from django.contrib.auth.views
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            try:
                # make sure the user is a subscriber, not an admin or something
                Subscriber.objects.get(pk=form.get_user().pk)
                from django.contrib.auth import login
                login(request, form.get_user())
                return HttpResponseRedirect("/")
            except:
                pass
    else:
        form = AuthenticationForm()
    return direct_to_template(request, "registration/login.html", {
            'form': form,
    })

    
def logout(request):
    d_logout(request)
    return HttpResponseRedirect("/")
    

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
    return direct_to_template(request,'fbmc_result_list.txt', {'objs': objs})