from datetime import datetime
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.hashcompat import md5_constructor
from django.utils.safestring import mark_safe
from crimsononline.content.models import *



def get_contributors(request):
    if request.method != 'GET':
        raise Http404
    q_str, limit = request.GET.get('q', ''), request.GET.get('limit', None)
    excludes = request.GET.get('exclude','').split(',')
    if excludes:
        excludes = [int(e) for e in excludes if e]
    if (len(q_str) < 1) or (not limit):
        raise Http404
    c = Contributor.objects.filter(
        Q(first_name__contains=q_str) | Q(last_name__contains=q_str),
        is_active=True).exclude(pk__in=excludes)[:limit]
    return render_to_response('contributors.txt', {'contributors': c})

def get_special_issues(request):
    """
    Returns an html fragment with special issues as <options>
    """
    if request.method != 'GET':
        raise Http404
    year = request.GET.get('year', '')
    if not year.isdigit():
        raise Http404
    year = int(year)
    issues = Issue.objects.special.filter(issue_date__year=year)
    return render_to_response('special_issues_fragment.html', 
        {'issues': issues, 'blank': '---'})

def get_issues(request):
    """
    Returns a dictionary of issue ids, indexed by issue date.
    """
    if request.method != 'GET':
        raise Http404
    year, month = request.GET.get('year', ''), request.GET.get('month', '')
    if not (year and month):
        raise Http404
    year, month = int(year), int(month)
    issues = Issue.objects.daily.filter(
        issue_date__year=year, issue_date__month=month)
    dict = {}
    for issue in issues:
        dict[issue.issue_date.strftime("%m/%d/%Y")] = issue.pk
    return HttpResponse(simplejson.dumps(dict))

# TODO: protect this
def get_imgs(request, page=None, pk=None):
    """
    Returns some JSON corresponding to a list of image thumbnails.
    These correspond to Image.objects.all() and are paginated.
    """
    
    if page is not None:
        IMGS_PER_REQ = 2
        json_dict, images = {}, {}
        
        p = Paginator(Image.objects.all(), IMGS_PER_REQ).page(page)
        imgs = p.object_list  
        for i in imgs:
            images[i.pk] = render_to_string('image_fragment.html', {'images': [i]})

        json_dict['images'] = images
        json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
        json_dict['prev_page'] = p.previous_page_number() if p.has_previous() else 0
        return HttpResponse(simplejson.dumps(json_dict))
        
    elif pk is not None:
        return render_to_response(
            'image_fragment.html', 
            {'images': [get_object_or_404(Image, pk=pk)]}
        )


MAX_IMGS_PER_GAL = 5
def get_img_gallery(request, type, pk):
    """
    Returns some JSON corresponding to an image gallery
    """
    if type == "img":
        dict = {'image': get_object_or_404(Image, pk=int(pk))}
    else:
        gal = get_object_or_404(ImageGallery, pk=int(pk))
        dict = {'images': gal.images.all()[:MAX_IMGS_PER_GAL],
                'gal': gal}
    return render_to_response('image_gal_fragment.html', dict)

# don't think this is used anymore
def get_img_galleries(request, st_yr, st_mnth, end_yr, 
                        end_mnth, tags, page=None):
    """
    Returns some JSON corresponding to a list of image galleries and images.
    """
    
    IMG_GALS_PER_REQ = 5
    
    tags = [tag.strip() for tag in tags.split(',')]
    st_yr, st_mnth, end_yr, end_mnth = \
        int(st_yr), int(st_mnth), int(end_yr), int(end_mnth)
    end_yr, end_mnth = (end_yr+1, 1) if end_mnth > 11 else (end_yr, end_mnth+1)
    page = int(page or 1)
    
    q = Q(created_on__range=(
        datetime(st_yr, st_mnth, 1),
        datetime(end_yr, end_mnth, 1),
    ))
    for tag in tags:
        q = q & Q(tags__text=tag)
    # TODO: loading all the objects at once is REALLY inefficient; fix it
    imgs = list(Image.objects.filter(q)) + list(ImageGallery.objects.filter(q))
    p = Paginator(imgs, IMG_GALS_PER_REQ).page(page)
    
    galleries = {}
    for obj in p.object_list:
        if obj.__class__ == ImageGallery:
            galleries['gal_%d' % obj.pk] = render_to_string('image_gal_fragment.html', {
                'images': obj.images.all()[:MAX_IMGS_PER_GAL],
                'more': max(obj.images.count() - MAX_IMGS_PER_GAL, 0),
                'gal': obj})
        else:
            galleries['img_%d' % obj.pk] = render_to_string('image_gal_fragment.html', {
                'image': obj,
            })
    
    json_dict = {}
    json_dict['galleries'] = galleries
    json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
    json_dict['prev_page'] = p.previous_page_number() if p.has_previous() else 0
    
    return HttpResponse(simplejson.dumps(json_dict))

def login_user(request):
    """
    Handles response from PIN application when a user tries to log in.
    """
    user = authenticate(huid=request.REQUEST["huid"])
    if user is not None:
        if user.is_active:
            login(request,user)
            contrib = Contributor.objects.get(user=user)
            if contrib is None:
                return HttpResponseRedirect('http://www.zombo.com')
            else:
                return HttpResponseRedirect('/admin/')
    else:
        return HttpResponseRedirect('http://www.youtube.com/watch?v=oHg5SJYRHA0')
    