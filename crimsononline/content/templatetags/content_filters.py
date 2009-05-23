from django import template
from django.template import defaultfilters as filter
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Article, Content, ContentGeneric
from crimsononline.common.templatetags.common_filters import linkify, human_list


register = template.Library()

@register.filter
def render(content, method):
    if not content:
        return ''
    try:
        if isinstance(content, ContentGeneric):
            content = content.content_object
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
def to_img_tag(img, size_spec):
    """Turns an Image into an img tag (html).
    
    @size_spec => the size spec of the display image. 3 possible formats:
        string name of the size_spec defined in the Image model
            (without the SIZE_ prefix),
        string formatted "WIDTH,HEIGHT,CROP_RATIO" or "WIDTH,HEIGHT", or
        tuple given as (WIDTH, HEIGHT, CROP_RATIO) or (WIDTH, HEIGHT)
     
    empty or omitted constraints are not binding
    empty crop ratio assume to be 0
    """
    size_spec = str(size_spec)
    # check to see if size_spec is a predefined attribute
    disp = getattr(img, size_spec, None)
    if not disp and size_spec.find(',') != -1:
        # finish converting tuple to string
        size_spec = size_spec.replace('(','').replace(')','')
        size_spec = tuple(size_spec.split(','))
        w = int(size_spec[0]) if size_spec[0] else None
        h = int(size_spec[1]) if size_spec[1] else None
        c = float(size_spec[2]) if len(size_spec) > 2 and size_spec[2] \
            else 0
        size_spec = (w, h, c)
        disp = img.display(*size_spec)
    k = filter.force_escape(img.kicker)
    tag = '<img src="%s" title="%s" alt="%s" />' % \
            (disp.url, k, k)
    return mark_safe(tag)

@register.filter
def to_thumb_tag(img):
    THUMB_SIZE = '96'
    return to_img_tag(img, THUMB_SIZE + ',' + THUMB_SIZE)