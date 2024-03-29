from re import compile, search, sub
import operator
from django import template
from django.contrib.flatpages.models import FlatPage
from django.template import defaultfilters as filter, resolve_variable, Template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from crimsononline.common.utils import misc
from crimsononline.common.utils.html import para_list
from crimsononline.common.utils.lists import first_or_none
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from xml.dom.minidom import *
from urllib import urlopen

register = template.Library()

@register.filter
def capchars(str, n):
    """Make str have at most n chars, broken at a space.

    Don't use this, truncchars is better.
    """
    try:
        n = int(n)
        if len(str) < n:
            return str
        return str[:n].rsplit(' ', 1)[0] + ' ...'
    except:
        return str

@register.filter
def truncchars(str, specifier):
    """Truncate str, at a whole word.

    Specifier is in the form
        n[,str]
    where n is an integer, and str is an optional suffix,
    which will be appended only if len(str) < n.
    """
    if specifier.find(',') is -1:
        specifier += ','
    n, suffix = tuple(specifier.split(','))
    if len(str) <= n:
        return str
    return str[:int(n)].rsplit(' ', 1)[0] + suffix

@register.filter
def notfirst(seq):
    """Return a list of everything but the first"""
    return seq[1:]

@register.filter
def first(seq):
    """Return the first item in the list"""
    try:
        return seq[0]
    except IndexError, TypeError:
        return ''

PML_RE = compile(r'\[([^\[^\]]+)\]')
N_RE = compile(r'\n\s+\n')
@register.filter
def profileml(s):
    """Turn [s] into <b>s</b>, and \n paragraphs into <p> paragraphs.
    TODO: not quite safe
    """
    s  = '<p>' + N_RE.sub('</p><p>', s) + '</p>'
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

@register.filter
def paragraphs(str):
    """Split str on <p> tags, mark output as save.

    Keep the <p> tags in the output.
    """
    return [mark_safe(x) for x in para_list(str)]


@register.filter
def newlines_to_paragraphs(str):
    """Return a <p> separated string, separating on newlines

    Keep the <p> tags in the output.
    """
    return [mark_safe("<p>%s</p>" % x) for x in str.split('\n') if len(sub(r'[\r\s\t]',"",x)) > 0]

@register.filter
def is_nav_cur(current, check):
    if current == check:
        return mark_safe('id="nav_cur"')
    else:
        return ''

@register.filter
def dlinkify(obj, domain=''):
    """Like linkify(), but with a domain prepended.

    Unfortunately, this makes link text much less customizable.
    """
    try:
        # if obj is not a list, convert it into a list
        if not getattr(obj, '__iter__', False):
            obj = [obj]
        l = [mark_safe('<a href="%s%s">%s</a>' % \
                (domain, i.get_absolute_url(), filter.force_escape(i))) for i in obj]
        # nonlists obj's should be returned as nonlists
        return l[0] if len(l) == 1 else l
    except IndexError:
        return ''


@register.filter
def linkify(obj, link_text=''):
    """turns object(s) into (html) link(s).

    if objects have the attr 'domain', stick the domain in the URL.
    """
    try:
        l = []
        # if obj is not a list, convert it into a list
        if not getattr(obj,'__iter__',False):
            obj = [obj]
        for item in obj:
            if link_text == '':
                l_text = item
            else: # if link_text is not ascii, can't call getattr on it
                try:
                    link_text = link_text.encode('ascii')
                    l_text = getattr(item, link_text, link_text)
                except UnicodeEncodeError:
                    l_text = link_text
            l.append(mark_safe('<a href="%s">%s</a>' % \
                (item.get_absolute_url(), filter.force_escape(l_text))))
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
            s += t % filter.conditional_escape(item)
        return mark_safe(s)

A_LINK_RE = compile(r'href=\"(.+)\"')
A_TEXT_RE = compile(r'>(.+)<')
class FlatpageNavNode(template.Node):
    def __init__(self, nodelist, prefix, cur_url, toplevelonly):
        self.prefix = ('' if prefix.startswith('/') else '/') + prefix
        self.prefix = self.prefix + ('' if prefix[-1] == '/' else '/')
        self.cur_url = template.Variable(cur_url)
        self.nodelist = nodelist
        self.toplevel = toplevelonly
        if self.toplevel:
            self.urldepth = self.prefix.count('/')

    def render(self, context):
        links = []
        splitnodes = self.nodelist.render(context).split("</a>")
        hardlinks = [x + "</a>" for x in splitnodes][:-1]

        for link in hardlinks:
            links.append((search(A_TEXT_RE, link).group(1), search(A_LINK_RE, link).group(1)))

        pages = FlatPage.objects.filter(url__startswith = self.prefix)
        if self.toplevel:
            pages = [p for p in pages if p.url.count('/') == self.urldepth + 1]
        for page in pages:
            links.append((page.title, page.url))

        links.sort()
        cur_url = self.cur_url.resolve(context)
        return mark_safe(render_to_string('templatetag/flatpagenav.html', locals()))


def do_flatpage_nav(parser, token):
    """Builds a navigation menu for flatpages by url

    inside of the flatpage_nav and endflatpage_nav templatetags, it's possible to
    put static links, which will be sorted and added to the navigation

    Usage:
        {% flatpage_nav "/url/root/" "/cur/url" toplevelonly %}
        <a href="/1">link1</a>
        <a href="/2">link2</a>
        {% endflatpage_nav %}

    toplevelonly is optional, and if specified, only adds urls of the form
    "/url/root/.*?/" (eg. omits /url/root/foo/bar/ but includes /url/root/foo/)
    """

    bits = token.split_contents()

    if len(bits) < 3:
        raise template.TemplateSyntaxError('%r tag requires 2 arguments.' % bits[0])

    prefix = bits[1]
    cur_url = bits[2]
    top_level_only = len(bits) > 3 and bits[3] == 'toplevelonly'
    nodelist = parser.parse(('endflatpage_nav',))
    parser.delete_first_token()

    return FlatpageNavNode(nodelist, prefix, cur_url, top_level_only)

register.tag('flatpage_nav', do_flatpage_nav)

class AdvertisementNode(template.Node):
    def __init__(self, zone):
        self.zone = zone

    def render(self, context):
        return render_to_string("templatetag/advertisement.html",{'zone': self.zone})

def advertisement(parser, token):
    """
    Renders an ad using the OpenX Account
    """
    bits = token.split_contents()

    if len(bits) != 2:
        raise template.TemplateSyntaxError('%r tag requires 1 argument.' % bits[0])

    zone = bits[1]
    return AdvertisementNode(zone)

advertisement = register.tag(advertisement)

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

class WeatherNode(template.Node):
    def __init__(self):
        pass

    def render(self, context):
        try:
            datasource = urlopen('http://rss.accuweather.com/rss/liveweather_rss'
                                 '.asp?metric=0&locCode=02138').read()
            wdom = parseString(datasource)
            cur_weather = wdom.getElementsByTagName("title")[2].childNodes[0].nodeValue

            temperature = str(cur_weather).split()[-1]
            currently = str(cur_weather).split(":")[1].lower()
            icon = ""
            if(currently.count("sun")>0):
                icon = "sun.gif"
            elif(currently.count("snow")>0):
                icon = "snow.gif"
            elif(currently.count("rain")>0):
                icon = "rain.gif"
            elif(currently.count("cloud")>0):
                icon = "cloud.gif"
            if icon:
                icon_txt = '<img alt="%s" src="%s" />' % (icon.split(".")[0], static_url('images/icons/' + icon))
            else:
                icon_txt = ""

            return'<a class="submenu_right" href="#">Cambridge, MA weather: %s</a><div class="submenu_image">%s</div>' % (str(cur_weather).split()[-1], icon_txt)
        except:
            # Don't raise exception if feed is down or something else
            return ''

def weather(parser, token):
    """A little weather widget (displays the temp) for the subnav."""
    bits = token.split_contents()
    return WeatherNode(*(bits[1:3]))
weather = register.tag(weather)

class TaglinksNode(template.Node):
    def __init__(self, linklist, urlbase):
        self.linklist = linklist
        self.urlbase = template.Variable(urlbase)

    def render(self, context):
        try:
            self.urlbase = self.urlbase.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        return render_to_string("templatetag/taglinks.html",{ 'linklist': self.linklist, 'url_base': self.urlbase })

def taglinks(parser, token):
    """
    Renders an ad using the OpenX Account
    """
    bits = token.split_contents()
    
    if len(bits) != 3:
        raise template.TemplateSyntaxError('%r tag requires 1 argument.' % bits[0])
    cmname = bits[1]
    
    try:
        srcm = ContentModule.objects.get(name=cmname)

        inputstrl = srcm.comment.strip().split('\n')
        tuplelist = []
        for tagset in inputstrl:
            tuplelist.append((tagset.split('=')[0].strip(), tagset.split('=')[1].strip()))
        
    except:
        tuplelist = []
    urlbase = bits[2]
    
    return TaglinksNode(tuplelist, urlbase)

taglinks = register.tag(taglinks)

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

    depends on the require_once function, defined in media_include.js and included
    in base.html
    """
    if link_to_js[:7] != 'http://':
        link_to_js = misc.static_content("scripts/%s" % link_to_js)
    return mark_safe('<script type="text/javascript">require_once("%s");</script>' \
        % link_to_js)

@register.simple_tag
def static_js_force(link_to_js):
    """
    renders a javascript include.
    make sure you use a url relative to the base javascript folder, or a link that
        starts with http://

    depends on the require_once function, defined in media_include.js and included
    in base.html
    """
    if link_to_js[:7] != 'http://':
        link_to_js = misc.static_content("scripts/%s" % link_to_js)
    return mark_safe('<script type="text/javascript" src="%s"></script>' % link_to_js)

@register.simple_tag
def latest_tagged_video(tag):
    """
    Returns the key of the latest video with the tag specified.
    """
    if not isinstance(tag, Tag):
        try:
            tag = Tag.objects.get(text=tag)
        except Tag.DoesNotExist:
            return mark_safe('')
    video = first_or_none(YouTubeVideo.objects.filter(tags=tag).order_by('-issue__issue_date'))
    if video:
        return mark_safe(video.key)
    return mark_safe('')