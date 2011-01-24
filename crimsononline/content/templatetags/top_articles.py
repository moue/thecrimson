from datetime import datetime, timedelta
from math import log
from string import split
import time
import urllib
from urlparse import urlparse
from django import template
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.urlresolvers import RegexURLResolver, Resolver404
from django.db import connection
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.utils import simplejson
from django.utils.safestring import mark_safe
from operator import itemgetter
try:
    from googleanalytics import Connection
except:
    Connection = None
from crimsononline.content.models import Image, Article, Content, Section, Contributor, Tag, MostReadArticles
from crimsononline.urls import CONTENT_URL_RE, CGROUP_URL_RE

D_USER_KEY = "vabqI2su93P1wVF3Ls9kXhXhRggV7y2ylokjq137yPAz47cY5dDMHgUA2QlZoWNE"
# The following is true for now
# D_FORUM_KEY = "9XGWB9o6NT1ZNiMtc2vt6ZJIUdp0D6sZDvis4hPfGGpsRaUchuH5c4fbO71GPAOj"
D_FORUM_KEY = "pkUMj0suYbfCUXu2hon1EB5xrgMLWADS9kNZiGtJ0ISE76QLyMvEb2SyPFmS3F5x"
D_FORUM_ID = "1508"

GA_LOGIN = "crimsonanalytics@gmail.com"
GA_PASS = "andylei:male"
GA_AID = "509545"

# Below values roughly based on values of 1/log(days + 1.5)
# Last day
TP1_FACTOR = 3.6
# Last week
TP2_FACTOR = 1.35
# Last month
TP3_FACTOR = 0.76
TP1_TIMEDELTA = timedelta(days = 1)
TP2_TIMEDELTA = timedelta(days = 7)
TP3_TIMEDELTA = timedelta(days = 30)

generic_obj_patterns = patterns('crimsononline.content.views',
    url('^' + CONTENT_URL_RE, 'get_content_obj', name='content_content'),
    url('^' + CGROUP_URL_RE + CONTENT_URL_RE + '$', 'get_grouped_content_obj',
        name='content_grouped_content'),
    url('^' + CGROUP_URL_RE + '$', 'get_content_group_obj',
        name='content_contentgroup'),
)

register = template.Library()

@register.tag(name="most_read_articles")
def compile_most_read(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 1:
        specifier = None
    elif len(tokens) == 2:
        specifier = tokens[1]
    else:
        raise template.TemplateSyntaxError, "%r tag requires 1 or 0 arguments" % tokens[0]
    return TopArticlesNode(specifier)

def safe_resolve(url, resolver):
    try:
        return resolver.resolve(url)
    except Resolver404:
        return None

def call_view(view, args):
    try:
        return view(*([None] + list(args)))
    except Content.DoesNotExist:
        return None

class TopArticlesNode(template.Node):
    """
    Generates the most read articles/most commented articles widget.

    Takes one argument, which should be a tag, author, or section within which to look.
    """
    def __init__(self, specifier):
        try:
            self.specifier = template.Variable(specifier)
        except:
            self.specifier = None

    def render(self, context):
        pre_title, post_title = "", ""
        if self.specifier:
            try:
                self.specifier = self.specifier.resolve(context)
            except:
                return ''
        else:
            self.specifier = ''
        """
        if not cache.get("mostreadarticles" + str(self.specifier).replace(' ', '')):
            # Create a resolver for the slightly modified URL patterns we defined above
            resolver = RegexURLResolver(r'^/', generic_obj_patterns)
            # Step 1: We want to get the most viewed articles from the database
            cursor = connection.cursor()
            orig_ss = self.specifier or ''
            if self.specifier:
                if isinstance(self.specifier, basestring):
                    parsedspec = self.specifier.split(":")
                    try:
                        if parsedspec[0] == "section":
                            self.specifier = Section.objects.filter(name=parsedspec[1])[0]
                    except:
                        return ''
                if self.specifier.__class__ == Section:
                    tableStr = ""
                    limitStr = " AND content_content.section_id = " + str(self.specifier.id)
                    try:
                        post_title = 'IN %s' % str(Section.objects.get(pk=self.specifier.id)).upper()
                    except:
                        pass
                elif self.specifier.__class__ == Contributor:
                    tableStr = ", content_contributor, content_content_contributors"
                    limitStr = " AND content_contributor.id = " + str(self.specifier.id) + \
                               " AND content_contributor.id = content_content_contributors.contributor_id" \
                               " AND content_content_contributors.content_id = content_content.id"
                    try:
                        pre_title = Contributor.objects.get(pk=self.specifier.id).first_name.upper() + "'S"
                    except:
                        pass
                elif self.specifier.__class__ == Tag:
                    tableStr = ", content_tag, content_content_tags"
                    limitStr = " AND content_tag.id = " + str(self.specifier.id) + \
                               " AND content_content_tags.content_id = content_content.id" \
                               " AND content_content_tags.tag_id = content_tag.id"
                    try:
                        post_title = 'IN "%s"' % Tag.objects.get(pk=self.specifier.id).text.upper()
                    except:
                        pass

                else:
                    raise template.TemplateSyntaxError, "The TopArticles tag can only take a section, contributor, or tag argument (%r passed)" % self.specifier.__class__
            else:
                tableStr = ""
                limitStr = ""
            if settings.DATABASE_ENGINE == 'sqlite3':
                seven_days_ago = " date('now', '-7 days') "
            elif settings.DATABASE_ENGINE == 'mysql':
                seven_days_ago = " ( NOW() - INTERVAL 7 day ) "
            # SO NON-SEXUALITY-NORMATIVE
            # Oh, a real comment in case someone comes upon this later: We're selecting article ID, content type ID, and a computed field called "hitindex"
            # which will eventually use log() for a better curve.  This ages articles' hits to reduce freshness.  Then it sorts by hitindex and returns the top 5.
            # TODO: Fix this to use proper decay when we switch to a real SQL server
            sqlstatement = "SELECT DISTINCT content_article.content_ptr_id, SUM(content_contenthits.hits) AS hitnum FROM content_article, " \
                           "content_content, content_contenthits" + tableStr + \
                           " WHERE content_content.id = content_article.content_ptr_id " \
                           " AND content_contenthits.content_id = content_content.id " \
                           " AND content_content.pub_status = 1 " \
                           " AND content_contenthits.date >" + seven_days_ago + limitStr + \
                           " GROUP BY content_contenthits.content_id ORDER BY hitnum DESC LIMIT 5"
            cursor.execute(sqlstatement)
            mostreadarticles = cursor.fetchall()
            try:
                mostreadarticles = [Content.objects.get(pk=x[0]).child for x in mostreadarticles]
                cache.set("mostreadarticles" + str(orig_ss).replace(' ', ''), mostreadarticles, 60 * 20)
            except:
                mostreadarticles = None
        else:
            mostreadarticles = cache.get("mostreadarticles" + str(self.specifier).replace(' ', ''))
        """
        mostreadarticles = None
        
        try:
            mostReadObj = MostReadArticles.objects.order_by('-create_date')[0]
            mostreadarticles = [mostReadObj.article1, mostReadObj.article2, mostReadObj.article3, mostReadObj.article4, mostReadObj.article5]
        except:
            mostreadarticles = None
            
        # TODO: uncomment / fix this.  it calls disqus every time, which is annoying
        mostcommentedarticles = None # delete this when below is uncommented
        # I think this all works, but I can't test it right now because there are no comments at the moment
        """
        # Step 2: Grab the JSON crap from Disqus and build another list of the most commented articles

        updated_threads_url = "http://disqus.com/api/get_updated_threads?user_api_key=" + D_USER_KEY + "&forum_id=" + D_FORUM_ID \
                            + "&api_version=1.1&since=" + (datetime.now() - timedelta(days=7) ).strftime('%Y-%m-%dT%H:%M')
        updated_threads = simplejson.load(urllib.urlopen(updated_threads_url))
        # sort the thread list
        updated_threads['message'].sort(lambda x, y: cmp(float(y['num_comments']), float(x['num_comments'])))

        # call resolver.resolve on everything in the list
        urllist = map(lambda x: (urlparse(x['url']))[2], updated_threads['message'])
        # Optimization: we assume that at least 5 of these 20 articles will not resolve to None
        if not self.specifier:
            del urllist[20:]
        threadobjlist = map(lambda x: safe_resolve(x, resolver), urllist)
        # Filter according to specifier
        # No error checking here since it should have happened before
        ""
        if self.specifier:
            if self.specifier.__class__ == Section:
                threadobjlist = [x for x in threadobjlist if x.section == self.specifier.id]
            elif self.specifier.__class__ == Contributor:
                threadobjlist = [x for x in threadobjlist if self.specifier.id in [x.id for x in threadobjlist.contributors]]
            elif self.specifier.__class__ == Tag:
                threadobjlist = [x for x in threadobjlist if self.specifier.id in [x.id for x in threadobjlist.tags]]
        ""

        if self.specifier:
            del threadobjlist[20:]

        # mostcommentedarticles = [x for x in map(lambda x: call_view(x[0], x[1]), filter(lambda x: x != None, threadobjlist)) if x is not None]
        mostcommentedarticles = [x for x in [call_view(threadobj[0], threadobj[1]) for threadobj in threadobjlist if threadobj is not None] if x is not None]
        # Only want top 10 -- we need to do this last because we're not guaranteed that there won't be some gaps in threadobjlist
        del mostcommentedarticles[5:]
        """

        return render_to_string('templatetag/mostreadarticles.html',
            {'mostreadarticles': mostreadarticles,
                'mostcommentedarticles': mostcommentedarticles,'pre_title': pre_title, 'post_title': post_title})