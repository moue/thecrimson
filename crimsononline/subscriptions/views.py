from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from subscriptions.forms import SubscriptionForm

def signup(request):
    if request.method == 'POST':
        # process a submitted form
        f = SubscriptionForm('POST')
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
        f = SubscriptionForm({'tags': tags, 'contributors': contributors,
            'sections': sections})
    return render_to_response('email/signup.html', {'form': f})
    