from re import compile, search
import operator
from django import template
from django.contrib.flatpages.models import FlatPage
from django.template import defaultfilters as filter
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from crimsononline.common.utils import misc

register = template.Library()

@register.filter
def notfirst(seq):
    """returns a list of everything but the first"""
    return seq[1:]

PML_RE = compile(r'\[([^\[^\]]+)\]')
@register.filter
def profileml(s):
    """
    Turns [str] into <b>str</b>
    TODO: not quite safe
    """
    return mark_safe(PML_RE.sub(r'<b>\1</b>', s))

@register.filter
def yuhkilabel(s, type="red"):
    """
    produces html for a yuhki label (curved, w/ red in background)
    
    available types: 
    "red" = red background, no border
    "gray" = white background, gray border
    "black" = media viewer inactive
    "blacktive" = media viewer active
    """
    return mark_safe(render_to_string('templatetag/yuhkilabel.html', locals()))

paragraph_re = compile(r'</p>\s+<p')
@register.filter
def paragraphs(str):
    """
    Breaks str into paragraphs using linebreak filter, then splits by <p>.
    Keeps the <p> tags in the output.
    """

    # remove whitespace between adjacent tags, replace with sentinel value
    str = paragraph_re.sub('</p>,,,<p', str)
    # split by sentinel value
    l = str.split(',,,')
    print [mark_safe(x) for x in l]
    return [mark_safe(x) for x in l]

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
            l_text = item if link_text == '' \
                else getattr(item, link_text, link_text)
            l.append(mark_safe('<a href="%s">%s</a>' % (item.get_absolute_url(),
                filter.force_escape(l_text))))
        # nonlists obj's should be returned as nonlists
        return l[0] if len(l) == 1 else l
    except IndexError:
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
            s += t % filter.escape(item)
        return mark_safe(s)

class FlatpageNavNode(template.Node):
    def __init__(self, nodelist, prefix, cur_url):
        self.prefix = prefix
        self.cur_url = template.Variable(cur_url)
        self.nodelist = nodelist
    
    def render(self, context):
        linkre = compile(r'href=\"(.+)\"')
        textre = compile(r'>(.+)<')

        links = []

        hardlinks = [x + "</a>" for x in self.nodelist[0].render(context).split("</a>")]
        hardlinks = hardlinks[0:len(hardlinks)-1]

        for link in hardlinks:
            links.append((search(textre, link).group(1), search(linkre, link).group(1)))

        pages = FlatPage.objects.filter(url__startswith = "/" + self.prefix)
        for page in pages:
            links.append((page.title, page.url))

        links.sort()
        cur_url = self.cur_url.resolve(context)
        return mark_safe(render_to_string('templatetag/flatpagenav.html', locals()))


def do_flatpage_nav(parser, token):
    """
    Builds a navigation menu for flatpages by pulling all articles with a given prefix
    
    inside of the flatpage_nav and endflatpage_nav templatetags, it's possible to put static links, which will be sorted and added to the navigation
    """

    bits = token.split_contents()

    if len(bits) != 3:
        raise template.TemplateSyntaxError('%r tag requires 2 arguments.' % bits[0])

    prefix = bits[1]
    cur_url = bits[2]
    nodelist = parser.parse(('endflatpage_nav',))
    parser.delete_first_token()

    return FlatpageNavNode(nodelist, prefix, cur_url)

register.tag('flatpage_nav', do_flatpage_nav)

class RepeatNode(template.Node):
    def __init__(self, nodelist, count):
        self.nodelist = nodelist
        self.count = template.Variable(count)
    
    def render(self, context):
        output = self.nodelist.render(context)
        return output * int(self.count.resolve(context))


def repeat(parser, token):
    """
    From: http://www.djangosnippets.org/snippets/1499/
    Repeats the containing text a certain number of times.
    
    Requires a single argument, an integer, to indicate the number of times to
    repeat the enclosing content.
    
    Example::
    
        {% repeat 3 %}foo{% endrepeat %}
    
    Yields::
    
        foofoofoo
    """
    bits = token.split_contents()
    
    if len(bits) != 2:
        raise template.TemplateSyntaxError('%r tag requires 1 argument.' % bits[0])
    
    count = bits[1]
    nodelist = parser.parse(('endrepeat',))
    parser.delete_first_token()
    return RepeatNode(nodelist, count)
repeat = register.tag(repeat)


FULL_IMG = """<img src="%s" alt="star_full" />""" \
    % misc.static_content('images/icons/star_full.png')
EMPTY_IMG = """<img src="%s" alt="star_empty" />""" \
    % misc.static_content('images/icons/star_empty.png')
class RatingNode(template.Node):
    def __init__(self, rating, rating_max):
        self.r = template.Variable(rating)
        self.r_max = template.Variable(rating_max)
    
    def render(self, context):
        self.r = self.r.resolve(context)
        self.r_max = self.r_max.resolve(context)
        output = []
        for i in range(0, int(self.r)):
            output.append(FULL_IMG)
        for i in range(0, int(self.r_max) - int(self.r)):
            output.append(EMPTY_IMG)
        return ' '.join(output)

def rating(parser, token):
    """
    produces nice ratings stars
    
    Example::
        {% rating 4 7 %}
    
    Yields::
        4 full stars followed by 3 empty stars
    """
    bits = token.split_contents()
    if len(bits) != 3:
        raise template.TemplateSyntaxError('%r tag requires 2 argument.' % bits[0])
    return RatingNode(*(bits[1:3]))
rating = register.tag(rating)


@register.simple_tag
def static_url(link):
    return mark_safe(misc.static_content(link))


@register.simple_tag
def static_css(link_to_css):
    """
    renders a css link.  
    make sure you use a url relative to the base css folder, or a link that
        starts with http://
    """
    if link_to_css[:7] != 'http://':
        link_to_css = misc.static_content("css/%s" % link_to_css)
    return mark_safe("""<link type="text/css" rel="stylesheet" href="%s" />""" \
        % link_to_css)


@register.simple_tag
def static_js(link_to_js):
    """
    renders a javascript include.
    make sure you use a url relative to the base javascript folder, or a link that
        starts with http://
    """
    if link_to_js[:7] != 'http://':
        link_to_js = misc.static_content("scripts/%s" % link_to_js)
    return mark_safe("""<script type="text/javascript" src="%s"></script>""" \
        % link_to_js)

