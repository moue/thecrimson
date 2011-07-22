from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
import datetime
import codecs

class Command(NoArgsCommand):
    help = "This command will build all of the RSS feeds"
    def handle_noargs(self, **options):
        
        numberOfStories = 25
        
        def buildItem(obj):
            #helper function to build individual items
            rStr = "<item>"
            rStr += "<title>"+ obj.headline+"</title>"
            rStr += "<link>http://www.thecrimson.com"+obj.get_absolute_url()+"</link>"
            desc = obj.teaser
            #desc = desc.encode("utf-8")
            rStr += "<description>" + desc+"</description>"
            rStr += "<pubDate>"+str(obj.created_on)+"</pubDate>"
            if obj.main_rel_content:
                try:
                    #rStr += "<media:content url='%s' />" % obj.main_rel_content.absolute_url
                    rStr += "<media:content url='%s' />" % obj.main_rel_content.display_url(Image.SIZE_STAND)
                except:
                    rStr += ""
            rStr += "<dc:creator xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            for i in obj.contributors.all():
                try:
                    rStr += i.first_name + " " + i.middle_name + " " + i.last_name +", "
                except:
                    rStr += i.first_name + " " + i.last_name +", "
            rStr = rStr[:-2]
            rStr += "</dc:creator>"
            rStr += "<guid>http://www.thecrimson.com"+obj.get_absolute_url()+"</guid>"
            rStr += "</item>"
            return rStr
            
        def buildHeaderInfo(title, description):
            rStr = "<title> The Harvard Crimson | " + title +"</title>"
            rStr += "<link>http://www.thecrimson.com/</link>"
            rStr += "<description>" + description + "</description>"
            rStr += "<language>en-us</language>"
            rStr += "<lastBuildDate>" +str(datetime.datetime.now())+"</lastBuildDate>"
            return rStr
        
        def writeFeed(loc, content):
            fc = open(loc, 'w')
            fc.write('hi')
            fc.close()
            f1 = codecs.open(loc,'r+','utf-8') #must specifically encode the file as utf-8 or you'll run into problems
            f1.write(content)
            f1.close()
        
        fileStart = '<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
        fileEnd = '</channel></rss>'

        #build the top news feed
        topNewsFeed = fileStart + buildHeaderInfo(" Top Stories","The Top Crimson Articles")
        tnStories = Article.objects.exclude(section=6).order_by('-issue__issue_date').exclude(priority__lte=5)[:numberOfStories]
        for x in tnStories:
            topNewsFeed += buildItem(x)
            
        topNewsFeed += fileEnd
        
        writeFeed('/home/sites/crimson/crimsononline/static/feeds/TopNews.xml', topNewsFeed)
        
        #build the latest news feed
        latestNewsFeed = fileStart + buildHeaderInfo(" Latest Stories","The Latest Crimson Articles")
        latestItems = Article.objects.exclude(section=6).order_by('-issue__issue_date')[:numberOfStories]
        for x in latestItems:
            latestNewsFeed += buildItem(x)
        
        latestNewsFeed += fileEnd
        
        writeFeed('/home/sites/crimson/crimsononline/static/feeds/LatestNews.xml', latestNewsFeed)
        
        #write the section feeds
        sections = ['arts','opinion','fm','news','sports','flyby']
        
        for i in sections:
            sectionObj = Section.objects.get(name__iexact=i)
            feedText = fileStart + buildHeaderInfo(" Latest Stories in %s" % i,"The Latest Crimson Articles in %s" % i)
            feedItems = Article.objects.filter(section=sectionObj.pk).order_by('-issue__issue_date')[:numberOfStories]
            for x in feedItems:
                feedText += buildItem(x)
            
            feedText += fileEnd
            writeFeed('/home/sites/crimson/crimsononline/static/feeds/'+i+'.xml', feedText)
            
        #return topNewsFeed