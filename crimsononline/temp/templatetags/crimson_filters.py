from django import template
from django.utils.safestring import mark_safe
from crimsononline.core.models import Image

register = template.Library()

@register.filter
def to_img_tag(img, width, height):
    tag = ''
    if isinstance(img, Image):
        # set zero dimensions to None
        width = width or None
        height = height or None
        tag = '<img src="%s" title="%s" />' % \
            (img.get_pic_sized_url(width, height), img.caption)
    return mark_safe(tag)

@register.filter
def to_thumb_tag(img):
    THUMB_SIZE = 96
    return to_img_tag(img, THUMB_SIZE, THUMB_SIZE)

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