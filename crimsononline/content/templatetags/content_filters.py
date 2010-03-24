from datetime import date, datetime
from django import template
from django.template import defaultfilters as filter
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Map, Article, Content, Marker, \
                                         YouTubeVideo, Gallery, FlashGraphic
from crimsononline.common.templatetags.common import linkify, human_list
from crimsononline.common.fields import size_spec_to_size, AutosizeImageFieldFile
from crimsononline.common.utils.html import para_list
from re import compile, search, sub, DOTALL

register = template.Library()

@register.filter
def render(content, method):
    if not content:
        return ''
    try:
        return mark_safe(content._render(method))
    except Exception, err:
        # pass
        raise
    return ''

@register.filter
def datify(cont):
    """A more natural way to express dates on content.

    Uses the modified date if its recent, otherwise, uses issue_date
    """
    issue = cont.issue.issue_date
    if(date.today() <= issue):
        secs_ago = (datetime.today() - cont.modified_on).seconds
        if secs_ago < 3600:
            value = (secs_ago/60)
            unit = 'minute'
        else:
            value = (secs_ago/3600)
            unit = 'hour'
    else:
        daysold = (date.today() - issue).days
        if daysold == 1:
            return 'Yesterday'
        elif daysold <= 10:
            value = daysold
            unit = 'day'
        else:
            return issue.strftime('%B %d, %Y')
    plural = 's' if value != 1 else ''
    return '%d %s%s ago' % (value, unit, plural)

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
    if float(content.height)/content.width >= float(450)/619 and \
       content.height >= 450:
        return 0
    else:
        ren_height = float(content.height)/content.width*619
        return (450-ren_height)/2

@register.filter
def img_gallery_margin(img):
    """Gets the margin needed for an image in a gallery (height 450px)"""
    if float(img.pic.height)/img.pic.width >= float(450)/619:
        if img.pic.height >=450:
            return 0
        return int(450-img.pic.height)/2
    else:
        ren_height = float(img.pic.height)/img.pic.width*619
        return int(450-ren_height)/2

@register.filter
def to_img_tag(img, size_spec):
    """Turns an Image or ImageGallery into an img tag (html).

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
    if img.__class__ is Content:
        img = img.child
    disp_url = img_url(img, size_spec)
    k = filter.force_escape(getattr(img, 'img_title', ''))
    tag = '<img src="%s" title="%s" alt="%s"/>' % (disp_url, k, k)
    return mark_safe(tag)

@register.filter
def img_url(img, size_spec):
    # oh lawd almighty
    if not img or not hasattr(img, 'display_url'):
        return ''
    upscale = False
    if isinstance(size_spec, tuple) or isinstance(size_spec, list):
        size_spec = [s or 0 for s in size_spec]
    else:
        # size_spec must be a string if it's not a tuple or list
        size_spec = str(size_spec)
        # This is a bit of a kludge -- it's to test whether the s_s has the
        # Upscale attribute specified
        if size_spec.count(',') == 4:
            size_spec, upscale = size_spec[:size_spec.rfind(',')], bool(size_spec[size_spec.rfind(',') + 1:].strip())
        s = getattr(Image, 'SIZE_' + size_spec, None)
        if not s:
            size_spec = size_spec.replace('(','').replace(')','')
            size_spec = [s or 0 for s in size_spec.split(',')]
            size_spec = [int(s) for s in size_spec]
        else:
            size_spec = s
    if len(size_spec) < 3:
        size_spec = list(size_spec[:2]) + [0,0]
    size_spec = tuple(size_spec)

    return mark_safe(img.display_url(size_spec, upscale=upscale))

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

    if(len(size.split(","))==2):
        dims = size.split(",")
        width=dims[0]
        height=dims[1]
    else:
        width=size
        height=size

    GMaps_key = "ABQIAAAA--Z_bVpXIL9HJpQ50CHbfRRi_j0U6kJrkFvY4-OX2XYmEAa76BS5oixsScFqNPn7f8shoeoOZviFMg"

    markerstr = ""
    markers = Marker.objects.filter(map__pk = map.pk)
    for marker in markers:
        markerstr = markerstr + str(marker.lat) + "," + str(marker.lng) + "|"

    tag = '<img src="http://maps.google.com/staticmap?center=%s,%s&zoom=%s&size=%sx%s&maptype=mobile&key=%s&sensor=false&markers=%s" />' % \
        (map.center_lat, map.center_lng, map.zoom_level, width, height, GMaps_key, markerstr)
    return mark_safe(tag)

@register.filter
def pretty_sport_name(sport):
    """ For use with the sports ticker - return the pretty name of the sport"""
    tuples = Article.SPORTS_TYPE_CHOICES
    for t in tuples:
        if t[0] == sport:
            return t[1]
    return ""

@register.filter
def rel_no_articles(rel_content):
    """The non articles in a list of rel_content"""
    return [c for c in rel_content if not isinstance(c.child, Article)]

@register.filter
def rel_articles(rel_content):
    """Return the articles in a list of rel_content."""
    return [c for c in rel_content if isinstance(c.child, Article)]

@register.filter
def byline(obj, type):
    """Get the byline from an article, properly pluralized"""
    str = 'By '

    count = obj.contributors.count()
    if count is 0:
        return filter.upper('No Writer Attributed')
    links = linkify(obj.contributors.all())
    str += human_list(links)

    if type == 'short':
        return mark_safe(str)

    # byline_type = getattr(obj, 'byline_type', None)
    if hasattr(obj,'byline_type'):
        byline_type = obj.get_byline_type_display()
    if byline_type is not None and byline_type != 'None':
        str += ', ' + byline_type.upper()
        str += filter.pluralize(count).upper()

    return mark_safe(str)

@register.filter
def fix_teaser(teaser):
    """Fixes the messed-up Flyby teasers that show up on writer pages."""
    teaser_paras = para_list(teaser)
    try:
        return teaser_paras[0]
    # I think this shouldn't happen, but better safe than sorry...
    except IndexError:
        return ''

@register.filter
def has_jump(flybyarticle):
    """Checks whether a Flyby article has content past the jump.  Returns
    a boolean value that tells the Flyby content list template whether to
    display the "continued" link."""
    if flybyarticle.teaser != "":
        fba_paras = para_list(flybyarticle.text)
        teaser_paras = para_list(flybyarticle.teaser)
        if len(fba_paras) > len(teaser_paras):
            return True
        else:
            return False
    else:
        return (flyby_teaser(flybyarticle) != "")

@register.filter
def flyby_teaser(flybyarticle):
    """Processes a flybyarticle, returning the portion before the jump
    assuming that the article uses the new jump tag method.  If it doesn't,
    it returns ""."""
    jumptagre = compile(r"(.*)<!--more-->", DOTALL)
    match = jumptagre.match(flybyarticle.text)
    # If we find the tag, return the captured stuff before it
    if match:
        return match.group(1)
    # If we don't find the tag, this article has no jump.  Return nothing so that
    # the template recognizes this and just spits out the text.
    else:
        return ""

@register.filter
def remove_flyby_jump(text):
    """Removes the <!--more--> tag from a Flyby article, replacing it with an
    <a name="jump"/> instead."""
    jumprepre = compile(r"<!--more-->")
    parsedtext = jumprepre.sub('<a name="jump"></a>', text)
    return parsedtext