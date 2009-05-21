import sys
from datetime import datetime, timedelta, date
from django.shortcuts import \
    render_to_response, get_object_or_404, get_list_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.contrib.flatpages.models import FlatPage
from crimsononline.content.models import *
from crimsononline.content_module.models import ContentModule
from crimsononline.common.utils.paginate import paginate
from django.core.mail import send_mail


def get_content(request, ctype, year, month, day, slug, pk, content_group=None):
    """
    View for displaying a piece of content on a page
    Validates the entire URL
    """
    c = get_content_obj(request, ctype, year, month, day, slug, pk, content_group)
    # redirect to canonical URL
    if request.path != c.get_absolute_url():
        return HttpResponseRedirect(c.get_absolute_url())
    return HttpResponse(c._render('page'))

def get_content_obj(request, ctype, year, month, day, slug, pk, content_group=None):
    """
    Retrieves a content object from the database (no validation of params)
    """
    c = ContentGeneric.objects.get(content_type__name=ctype, object_id=int(pk))
    return c.content_object
    
def get_grouped_content(request, gtype, gname, ctype, year, month, day, slug, pk):
    """
    View for displaying a piece of grouped content on a page
    Validates the entire url
    """
    # validate the contentgroup
    cg = get_grouped_content_obj(request, gtype, gname, ctype, 
        year, month, day, slug, pk)
    if cg:
        return get_content(request, ctype, year, month, day, slug, pk, cg)
    else:
        raise Http404

def get_grouped_content_obj(request, gtype, gname, ctype, year, month, day, slug, pk):
    cg = ContentGroup.by_name(gtype, gname)
    return cg
        
def get_content_group(request, gtype, gname):
    """
    View for a Content Group
    """
    # validate the contentgroup
    cg = get_content_group_obj(gtype, gname)
    if not cg:
        raise Http404
    c = cg.contentgeneric_set.all()
    return render_to_response('contentgroup.html', {'cg': cg, 'content': c})

def get_content_group_obj(request, gtype, gname):
    cg = ContentGroup.by_name(gtype, gname)
    return cg

def index(request):
    issue = Issue.get_current()
    stories = top_articles('News')[:9]
    
    dict = {}
    dict['nav'] = 'index'
    dict['top_stories'] = stories[:4]
    dict['more_stories'] = stories[4:9]
    dict['opeds'] = top_articles('Opinion')[:6]
    dict['arts'] = top_articles('Arts')[:6]
    dict['sports'] = top_articles('Sports')[:6]
    dict['fms'] = top_articles('FM')[:6]
    dict['issue'] = issue
    dict['rotate'] = stories[:4]
    #dict['markers'] = Marker.objects.filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('index.html', dict)

def bigmap(request):
    stories = top_articles('News')[:20] # how many articles to show markers from...we will have to play with this
    dict = {}
    dict['markers'] = Marker.objects.distinct().filter(map__in = Map.objects.filter(article__in = stories.values('pk').query).values('pk').query)
    
    return render_to_response('bigmap.html', dict)
    
def writer(request, contributor_id, f_name, m_name, l_name, page=None):
    w = get_object_or_404(Contributor, pk=contributor_id)
    # Validate the URL (we don't want /writer/281/Balls_Q_McTitties to be valid)
    if (w.first_name, w.middle_initial, w.last_name) != (f_name, m_name, l_name):
        return HttpResponseRedirect(w.get_absolute_url())
    
    d = paginate(w.content.all(), page, 10)
    d.update({'writer': w, 'url': w.get_absolute_url()})
    
    return render_to_response('writer.html', d)

def tag(request, tag, page=None):
    tag = get_object_or_404(Tag, text=tag.replace('_', ' '))
    content = ContentGeneric.objects.filter(tags=tag)
    
    # top articles
    articles = ContentGeneric.objects.type(Article).filter(tags=tag)
    featured_articles = list(articles.filter(
        issue__issue_date__gte=last_month()).order_by('-priority')[:5])
    if len(featured_articles) < 5:
        featured_articles += list(articles.filter(
            issue__issue_date__gte=last_year(), 
            issue__issue_date__lte=last_month()).order_by('-priority')[:5])
    if len(featured_articles) < 5:
        featured_articles += list(articles.filter( 
            issue__issue_date__lte=last_year()).order_by('-priority')[:5])
    featured_articles = featured_articles[:5]
    
    # TODO: top writers (contributors that have the most content with this tag)
    
    # TODO: related tags (tags with most shared content)
    #content_pks = [d['id'] for d in content.values('id')]
    #rel_tags = Tag.objects.filter(content__id__in=content_pks).annotate(
    
    
    d = paginate(content, page, 5)
    d.update({'tag': tag, 'url': tag.get_absolute_url(), 
        'featured': featured_articles})
    
    return render_to_response('tag.html', d)

def section(request, section, issue_id=None, tags=None):    
    # validate the section (we don't want /section/balls/ to be a valid url)
    if section == 'photo':
        return photo(request)
    section = filter(lambda x: section.lower() == x.name.lower(), Section.all())
    if len(section) == 0:
        raise Http404
    section = section[0]
    
    # grab the correct issue
    if issue_id is None:
        issue = Issue.get_current()
    else:
        issue = get_object_or_404(Issue, pk=issue_id)
    
    content = ContentGeneric.objects.recent.filter(section__pk=section.pk)
    # filter based on tags
    if tags:
        tags = tags.lower().replace('_',' ').split(',')
        for tag in tags:
            content = content.filter(tags__text=tag)
    content = content[:20]
    
    dict = {
        'nav': section.name.lower(),
        'issue': issue,
        'content': content,
        'section': section.name.capitalize(),
        'tags': tags,
    }
    return render_to_response(
        [dict['nav']+'.html', 'section.html', 'content_list.html'], dict
    )

def photo(request):
    galleries = ImageGallery.objects.order_by('-created_on')[:10]
    nav, title = 'photo', 'Photo'
    return render_to_response('photo.html', locals())
    
def gallery(request, currentimg_id, gallery_id):
    currentimg_id = int(currentimg_id)
    gallery_id = int(gallery_id)
    image = get_object_or_404(Image, pk=currentimg_id)
    gallery = get_object_or_404(ImageGallery, pk=gallery_id)
    return render_to_response('gallery.html', {'currentimg':image, 'gallery':gallery})

def subscribe(request):
	if request.method == 'POST':
		form = SubscriptionForm(request.POST)
		if form.is_valid():
			form.save()
			#send_mail('Your Harvard Crimson Subscription', 'yay!', 'subscriptions@thecrimson.com', [form.cleaned_data['email']], fail_silently=False)
			return HttpResponseRedirect('/done')
	else:
		form = SubscriptionForm()
	return render_to_response('subscription.html', {'form': form,})

def subscribed(request):
	return render_to_response('done.html')

#====== ajax stuff ==========#
def ajax_get_img(request, pk):
    image = get_object_or_404(Image, pk=pk)
    url = image.display(500, 500).url
    return render_to_response('ajax_get_image.html', locals())
    
    
# =========== view helpers ============== #
def top_articles(section):
    """returns the most recent articles from @section"""
    return Article.objects.recent.filter(generic__section__name=section)

def last_month():
    return date.today() + timedelta(days=-30)

def last_year():
    return date.today() + timedelta(days=-365)