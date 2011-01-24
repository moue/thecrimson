from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
import datetime
from django.db import connection

class Command(NoArgsCommand):
    help = "This command will create a new most read article row"
    def handle_noargs(self, **options):
        cursor = connection.cursor()
        seven_days_ago = " ( NOW() - INTERVAL 7 month ) "
        tableStr = ""
        limitStr = ""
        #as was pointed out the in the original comments in top_articles.py, this is probably a terrible way to do this, but given time constraints, doing it like this should resolve the stability issues we had
        
        sqlstatement = "SELECT DISTINCT content_article.content_ptr_id, SUM(content_contenthits.hits) AS hitnum FROM content_article, " \
                           "content_content, content_contenthits" + tableStr + \
                           " WHERE content_content.id = content_article.content_ptr_id " \
                           " AND content_contenthits.content_id = content_content.id " \
                           " AND content_content.pub_status = 1 " \
                           " AND content_contenthits.date >" + seven_days_ago + limitStr + \
                           " GROUP BY content_contenthits.content_id ORDER BY hitnum DESC LIMIT 5"
        
        cursor.execute(sqlstatement)
        mostreadarticle = cursor.fetchall()
        try:
            mostreadarticle = [Content.objects.get(pk=x[0]).child for x in mostreadarticle]
        except:
            mostreadarticle = None
        
        if mostreadarticle != None and len(mostreadarticle) > 4:
            #mr = MostReadArticles(article1=mostreadarticle[0], article2=mostreadarticle[1], article3=mostreadarticle[2], article4=mostreadarticle[3], article5=mostreadarticle[4]) 
            #mr.save()
            #return "Success"
        else:
            #return "Failure"
            var = "f"
        return MostReadArticles.objects.order_by('create_date')[0]