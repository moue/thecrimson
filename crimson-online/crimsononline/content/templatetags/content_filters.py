from django import template
from django.template import defaultfilters as filter
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Map, Article, Content, Marker
from crimsononline.common.templatetags.common import linkify, human_list
from crimsononline.common.forms import size_spec_to_size


register = template.Library()

@register.filter
def render(content, method):
    if not content:
        return ''
    try:
        return mark_safe(content._render(method))
    except Exception, err:
        print err, content, method
    return ''

@register.filter
def to_img_layout(img, dimensions):
    tag = ''
    if isinstance(img, Image):
        width, height = img.pic.width, img.pic.height
        w_constr, h_constr = tuple(dimensions.split(',')[:2])
        if width > height:
            type = 'wide'
            w_constr = str(int(int(w_constr) * 0.65) if w_constr else width)
        else:
            type = 'tall'
            w_constr = str(int(int(w_constr) * 0.40) if w_constr else width)
        img_tag = to_img_tag(img, w_constr + ',' + h_constr)
        tag = """<div class="%s_photo">%s
            <p class="byline">%s</p>
            <p class="caption">%s</p>
            </div>""" % (type, img_tag, linkify(img.contributor), 
                filter.force_escape(img.caption))
    return mark_safe(tag)

@register.filter
def flash_gallery_margin(img):
    """Gets the margin needed for a flash graphic in a gallery (height 450px)"""
    if float(content.height)/content.width >= float(450)/619 and content.height >= 450:
        return 0
    else:
        ren_height = float(content.height)/content.width*619
        return (450-ren_height)/2

@register.filter
def img_gallery_margin(img):
    """Gets the margin needed for an image in a gallery (height 450px)"""
    if float(img.pic.height)/img.pic.width >= float(450)/619 and img.pic.height >=450:
        return 0
    else:
        ren_height = float(img.pic.height)/img.pic.width*619
        return (450-ren_height)/2

@register.filter
def to_img_tag(img, size_spec):
    """Turns an Image into an img tag (html).
    
    @size_spec => the size spec of the display image. 3 possible formats:
        string name of the size_spec defined in the Image model
            (without the SIZE_ prefix),
        string formatted "WIDTH,HEIGHT,CROP_W,CROP_H" or "WIDTH,HEIGHT", or
        tuple given as (WIDTH, HEIGHT, CROP_W, CROP_H) or (WIDTH, HEIGHT)
     
    empty or omitted constraints are not binding
    any empty or zero crop parameter = no cropping
    """
    if img is None:
        return ''
    disp_url = img_url(img, size_spec)
    if hasattr(img, 'kicker'):
        k = filter.force_escape(img.kicker)
    else:
        k = ''
    tag = '<img src="%s" title="%s" alt="%s"/>' % \
            (disp_url, k, k)
    return mark_safe(tag)

@register.filter
def img_url(img, size_spec):
    if not img:
        return ''
    if isinstance(size_spec, tuple) or isinstance(size_spec, list):
        size_spec = [s or 0 for s in size_spec]
    else:
        size_spec = str(size_spec)
        s = getattr(img, 'SIZE_' + size_spec, None)
        if not s:
            size_spec = size_spec.replace('(','').replace(')','')
            size_spec = [s or 0 for s in size_spec.split(',')]
            size_spec = [int(s) for s in size_spec]
        else:
            size_spec = s
    if len(size_spec) < 3:
        size_spec = list(size_spec[:2]) + [0,0]
    size_spec = tuple(size_spec)
    
    return mark_safe(img.display_url(size_spec))
    
@register.filter
def to_thumb_tag(img):
    THUMB_SIZE = 96
    return to_img_tag(img, (THUMB_SIZE, THUMB_SIZE))
    
@register.filter
def to_map_thumb(map, size):
    """ Gets the url of a static image for a map
    
    @width, @height => width and height of box
    
    TODO: cache this
    """
    
    GMaps_key = "ABQIAAAA--Z_bVpXIL9HJpQ50CHbfRRi_j0U6kJrkFvY4-OX2XYmEAa76BS5oixsScFqNPn7f8shoeoOZviFMg"

    markerstr = ""
    markers = Marker.objects.filter(map__pk = map.pk)
    for marker in markers:
        markerstr = markerstr + str(marker.lat) + "," + str(marker.lng) + "|"
    
    tag = '<img src="http://maps.google.com/staticmap?center=%s,%s&zoom=%s&size=%sx%s&maptype=mobile&key=%s&sensor=false&markers=%s" />' % \
        (map.center_lat, map.center_lng, map.zoom_level, size, size, GMaps_key, markerstr)
    return mark_safe(tag)
    