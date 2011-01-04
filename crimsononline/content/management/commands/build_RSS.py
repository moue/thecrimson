from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *

class Command(NoArgsCommand):
    help = "This command will build all of the RSS feeds"
    def handle_noargs(self, **options):
        
        def buildItem(obj):
            #helper function to build individual items
            rStr = "<item>"
            rStr += "<title>"+ obj.headline+"</title>"
            rStr += "<link>"+obj.get_absolute_url()+"</link>"
            rStr += "<description>" + obj.teaser+"</description>"
            rStr += "<dc:creator xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            for i in obj.contributors.all():
                rStr += i.first_name + " " +i.last_name +", "
            rStr = rStr[:-2]
            rStr += "</dc:creator>"
            rStr += "<guid>"+obj.get_absolute_url()+"</guid>"
            rStr += "</item>"
            return rStr
            
        test = Article.objects.exclude(section=6).order_by('-issue__issue_date')[:1]
        #build the top news feed
        
        return buildItem(test[0])