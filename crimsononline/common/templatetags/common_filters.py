from re import compile
from django import template
from django.template import defaultfilters as filter
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import cgi

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
def yuhkilabel(s, inverted=False):
    """
    produces html for a yuhki label (curved, w/ red in background)
    """
    return mark_safe(render_to_string('templatetag/yuhkilabel.html', locals()))

@register.filter
def paragraphs(str):
    """
    Breaks str into paragraphs using linebreak filter, then splits by <p>.
    Keeps the <p> tags in the output.
    """
    str = filter.force_escape(str)
    str = filter.linebreaks(str)
    # remove whitespace between adjacent tags, replace with sentinel value
    r = compile(r'>\s+<')
    str = r.sub('>,,,<', str)
    # split by sentinel value
    l = str.split(',,,')
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