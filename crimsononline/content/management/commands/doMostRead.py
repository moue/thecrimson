from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
import datetime
from django.db import connection
import gdata.analytics.client
import gdata.sample_util

class Command(NoArgsCommand):
    help = "This command will create a new most read article row"
    def handle_noargs(self, **options):
        SOURCE_APP_Name = 'thecrimson.com'
        my_client = gdata.analytics.client.AnalyticsClient(source=SOURCE_APP_Name)
        
        try:
          my_client.client_login("thc.analytics","lizwoodley", source=SOURCE_APP_Name, service=my_client.auth_service)
        except gdata.client.BadAuthentication:
          exit('Invalid user credentials given.')
        except gdata.client.Error:
          exit('Login Error')
        
        now = datetime.datetime.now()
        dateChange = datetime.timedelta(days=-2)
        startDate = now + dateChange
        
        data_query = gdata.analytics.client.DataFeedQuery({
            'ids': 'ga:509545',
            'start-date': startDate.strftime("%Y-%m-%d"),
            'end-date': now.strftime("%Y-%m-%d"),
            'dimensions': 'ga:pagePath',
            'metrics': 'ga:pageviews,ga:uniquePageviews,ga:timeOnPage,ga:bounces,ga:entrances,ga:exits',
            'sort': '-ga:pageviews',
            'filters': 'ga:pagePath=@/article/',
            'max-results': '5'})

        self.feed = my_client.GetDataFeed(data_query)
        slugList = []
        for e in self.feed.entry:
            for m in e.dimension:
                tempStr = m.value[:-1]
                slugList.append(tempStr[tempStr.rfind("/")+1:])
        
        articleList = []
        for s in slugList:
            try:
                articleList.append(Content.objects.get(slug=s))
            except:
                str1 ="DoNothing"
        
        if len(articleList) == 5:
            mr = MostReadArticles(article1=articleList[0], article2=articleList[1], article3=articleList[2], article4=articleList[3], article5=articleList[4])
            mr.save()
            
        #return articleList
        