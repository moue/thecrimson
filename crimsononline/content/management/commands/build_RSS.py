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
                    rStr += "<media:content url='%s' />" % obj.main_rel_content.youtube_url
                except:
                    try:
                        rStr += "<media:content url='%s' />" % obj.main_rel_content.display_url(Image.SIZE_STAND)
                    except:
                        rStr += ""
                try:
                    rStr += "<media:thumbnail url='%s' />" % obj.main_rel_content.display_url(Image.SIZE_STAND)
                except:
                    try: 
                        rStr += "<media:thumbnail url='%s' />" % obj.main_rel_content.pic
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
            rStr += "<content:encoded><![CDATA["+obj.text+"]</content:encoded>"
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
        
        fileStart = '<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>'
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
        
        '''
        for i in sections:
            sectionObj = Section.objects.get(name__iexact=i)
            feedText = fileStart + buildHeaderInfo(" Latest Stories in %s" % i,"The Latest Crimson Articles in %s" % i)
            feedItems = Article.objects.filter(section=sectionObj.pk).order_by('-issue__issue_date')[:numberOfStories]
            for x in feedItems:
                feedText += buildItem(x)
            
            feedText += fileEnd
            writeFeed('/home/sites/crimson/crimsononline/static/feeds/'+i+'.xml', feedText)
        '''
        feedDate = date.today()-timedelta(days=7)

        allStories = Article.objects.filter(issue__issue_date__gt=feedDate).order_by('-issue__issue_date')
        arts = []
        opinion = []
        fm = []
        news = []
        sports = []
        flyby = []
        for i in allStories:
            if i.section.name.lower() == 'news':
                news.append(i)
            elif i.section.name.lower() == 'arts':
                arts.append(i)
            elif i.section.name.lower() == 'opinion':
                opinion.append(i)
            elif i.section.name.lower() == 'fm':
                fm.append(i)
            elif i.section.name.lower() == 'sports':
                sports.append(i)
            elif i.section.name.lower() == 'flyby':
                flyby.append(i)
            else:
                x = 0
        sectionDic = {}
        sectionDic.setdefault('arts',arts[:numberOfStories])
        sectionDic.setdefault('opinion',opinion[:numberOfStories])
        sectionDic.setdefault('fm',fm[:numberOfStories])
        sectionDic.setdefault('news',news[:numberOfStories])
        sectionDic.setdefault('sports',sports[:numberOfStories])
        sectionDic.setdefault('flyby',flyby[:numberOfStories])
        
        for k, v in sectionDic.iteritems():
            feedText = fileStart + buildHeaderInfo(" Latest Stories in %s" % k,"The Latest Crimson Articles in %s" % k)
            for x in v:
                feedText += buildItem(x)
            
            feedText += fileEnd
            writeFeed('/home/sites/crimson/crimsononline/static/feeds/'+k+'.xml', feedText)
            
        #return topNewsFeed