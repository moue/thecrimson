from django import template
from django.utils.safestring import mark_safe
from crimsononline.core.models import Image, Article, Content, ContentGeneric

register = template.Library()

@register.filter
def render(content, method):
    try:
        if isinstance(content, ContentGeneric):
            content = content.content_object
        return mark_safe(content._render(method))
    except Exception, err:
        print err
    return ''
    
    
@register.filter
def article_preview(article):
    tag = ''
    if isinstance(article, Article):
        tag = """<h3>%s</h3>
        <span class="byline">By %s</span>
        <p class="teaser">%s</p>
        """ % (
            linkify(article), 
            human_list(linkify(article.contributors.all())),
            article.teaser,
        )
    return mark_safe(tag)

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
            </div>""" % (type, img_tag, linkify(img.contributor), img.caption)
    return mark_safe(tag)

@register.filter
def to_img_tag(img, dimensions):
    """Turns an Image into an img tag (html).
    dimensions is the dimension constraint.  It should be a string formattted
     "WIDTH,HEIGHT".  Empty width or height is interpreted as a non-constraint.
    """
    tag = ''
    if isinstance(img, Image) and dimensions.find(',') != -1:
        width, height = tuple(dimensions.split(',')[:2])
        width = int(width) if width else None
        height = int(height) if height else None
        tag = '<img src="%s" title="%s" alt="%s" />' % \
            (img.display(width, height).url, img.caption, img.caption)
    return mark_safe(tag)

@register.filter
def to_thumb_tag(img):
    THUMB_SIZE = '96'
    return to_img_tag(img, THUMB_SIZE + ',' + THUMB_SIZE)

@register.filter
def is_nav_cur(current, check):
    if current == check:
        return mark_safe('id="nav_cur"')
    else:
        return ''
        
@register.filter
def linkify(obj, link_text=''):
    """turns object(s) into (html) link(s)"""
    try:
        l = []
        # if obj is not a list, convert it into a list
        if not getattr(obj,'__iter__',False):
            obj = [obj]
        for item in obj:
            l_text = item if link_text == '' else getattr(item, link_text, link_text)
            l.append(mark_safe('<a href="%s">%s</a>' % (item.get_absolute_url(), 
                                                        l_text)))
        # nonlists obj's should be returned as nonlists
        return l[0] if len(l) == 1 else l
    except:
        return ''
        
@register.filter
def human_list(list, connector='and'):
    """turns list into an comma separated list (with an and)"""
    # we don't want to listify non iterables
    if not getattr(list, '__iter__', False):
        return list
    else:
        s = ''
        l = len(list) - 1
        for i, item in enumerate(list):
            if i == 0:
                t = '%s'
            elif i == l and l > 1:
                t = ', ' + connector + ' %s'
            elif i == l and l == 1:
                t = ' ' + connector + ' %s'
            else:
                t = ', %s'
            s += t % item
        return mark_safe(s)