from datetime import datetime
from django.db import connection
from django.shortcuts import render_to_response, get_object_or_404
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson
from crimsononline.core.models import Image, ImageGallery

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
        
def get_img_galleries(request, st_yr, st_mnth, end_yr, 
                        end_mnth, tags, page=None):
    """
    Returns some JSON corresponding to a list of image galleries.
    """
    IMG_GALS_PER_REQ = 6
    
    tags = [tag.strip() for tag in tags.split(',')]
    st_yr, st_mnth, end_yr, end_mnth = \
        int(st_yr), int(st_mnth), int(end_yr), int(end_mnth)
    end_yr, end_mnth = (end_yr+1, 1) if end_mnth > 11 else (end_yr, end_mnth+1)
    page = int(page or 1)
    qs = ImageGallery.objects.filter(created_on__range=(
        datetime(st_yr, st_mnth, 1),
        datetime(end_yr, end_mnth, 1),
    ))
    for tag in tags:
        qs = qs & ImageGallery.objects.filter(tags__text=tag)
    p = Paginator(qs, IMG_GALS_PER_REQ).page(page)
    
    galleries = {}
    for gal in p.object_list:
        galleries[gal.pk] = render_to_string('image_gal_fragment.html', {'gal': gal})
        
    json_dict = {}
    json_dict['galleries'] = galleries
    json_dict['next_page'] = p.next_page_number() if p.has_next() else 0
    json_dict['prev_page'] = p.previous_page_number() if p.has_previous() else 0
    
    return HttpResponse(simplejson.dumps(json_dict))