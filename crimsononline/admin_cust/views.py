from datetime import datetime, timedelta
import re

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.flatpages.views import flatpage
from django.core import urlresolvers
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.hashcompat import md5_constructor
from django.utils.safestring import mark_safe

from crimsononline.content.models import *
from crimsononline.content.views import rotatables, \
    get_content, get_grouped_content, get_content_obj

def help(request):
    """Wrapper to admin lock requests to /admin/help/*.  Loads flatpage."""
    url = request.path.replace('/admin/help', '')
    return flatpage(request, url)
    
def content_to_admin(request, pth):
    if not pth.startswith('/'):
        pth = '/' + pth
    try:
        view, args, kwargs = urlresolvers.resolve(pth)
    except urlresolvers.Resolver404:
        return HttpResponseRedirect('/admin/')
    if view is not get_content and view is not get_grouped_content:
        return HttpResponseRedirect('/admin/')
    try:
        c = get_content_obj(request, *args, **kwargs)
    except Content.DoesNotExist:
        return HttpResponseRedirect('/admin/')
    return HttpResponseRedirect(c.get_admin_change_url())
    

def rotator_items(request, section='front'):
    if section == 'front':
        content = rotatables()
    else:
        try:
            content = rotatables(Section.cached(section))
        except:
            raise Http404
    output = ['<html><head></head><body><table><th><td>pk</td><td>ct</td><td>slug</td></th>']
    tmpl = "<tr><td><a href='%s'>%d</a></td><td>%s</td><td>%s</td></tr>"
    for c in content:
        link = c.get_admin_change_url()
        output += [tmpl % (link, c.pk, c.content_type, c.slug)]
    
    output.append('</table></body></html>')
    return HttpResponse('\n'.join(output))

def flush_cache(request):
    """Flush memcached"""
    if settings.CACHE_BACKEND.find('memcache') != -1:
        from django.core.cache import cache
        cache._cache.flush_all()
        return HttpResponse("Success")
    return HttpResponse("Failure")

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
def get_gallery(request, type, pk):
    """
    Returns some JSON corresponding to an image gallery
    """
    if type == "img":
        dict = {'image': get_object_or_404(Image, pk=int(pk))}
    else:
        gal = get_object_or_404(Gallery, pk=int(pk))
        dict = {'images': gal.images.all()[:MAX_IMGS_PER_GAL],
                'gal': gal}
    return render_to_response('image_gal_fragment.html', dict)

# don't think this is used anymore
def get_galleries(request, st_yr, st_mnth, end_yr, 
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
    imgs = list(Image.objects.filter(q)) + list(Gallery.objects.filter(q))
    p = Paginator(imgs, IMG_GALS_PER_REQ).page(page)
    
    galleries = {}
    for obj in p.object_list:
        if obj.__class__ == Gallery:
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
    
