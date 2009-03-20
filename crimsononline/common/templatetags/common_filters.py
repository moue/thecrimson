from django import template
from django.utils.safestring import mark_safe

register = template.Library()

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
            s += t % item
        return mark_safe(s)