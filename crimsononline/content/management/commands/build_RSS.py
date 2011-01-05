from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
import datetime

class Command(NoArgsCommand):
    help = "This command will build all of the RSS feeds"
    def handle_noargs(self, **options):
        
        numberOfStories = 25
        
        def buildItem(obj):
            #helper function to build individual items
            rStr = "<item>"
            rStr += "<title>"+ obj.headline+"</title>"
            rStr += "<link>"+obj.get_absolute_url()+"</link>"
            desc = repr(obj.teaser)
            desc = desc.encode("utf-8")
            rStr += "<description>" + desc+"</description>"
            rStr += "<dc:creator xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            for i in obj.contributors.all():
                rStr += i.first_name + " " +i.last_name +", "
            rStr = rStr[:-2]
            rStr += "</dc:creator>"
            rStr += "<guid>"+obj.get_absolute_url()+"</guid>"
            rStr += "</item>"
            return rStr
            
        def buildHeaderInfo(title, description):
            rStr = "<title> The Harvard Crimson | " + title +"</title>"
            rStr += "<link>http://www.thecrimson.com/</link>"
            rStr += "<description>" + description + "</description>"
            rStr += "<language>en-us</language>"
            rStr += "<lastBuildDate>" +str(datetime.datetime.now())+"</lastBuildDate>"
            return rStr
            
        fileStart = '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>'
        fileEnd = '</channel></rss>'

        #build the top news feed
        topNewsFeed = fileStart + buildHeaderInfo(" Top Stories","The top Crimson articles")
        tnStories = Article.objects.exclude(section=6).order_by('-issue__issue_date')[:numberOfStories]
        for x in tnStories:
            topNewsFeed += buildItem(x)
            
        topNewsFeed += fileEnd
        
        f1 = open('/home/sites/crimson/crimsononline/feeds/TopNews.xml','r+')
        f1.write(topNewsFeed)
        topNewsFeed = f1.read()
        topNewsFeed = topNewsFeed.replace("u'","").replace("'<","<")
        f1.write(topNewsFeed)
        f1.close()
        
        #return topNewsFeed