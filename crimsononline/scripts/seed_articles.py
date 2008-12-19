""" this is doomed to failure. thecrimson.com's html has MISMATCHED TAGS"""

import urllib
from xml.dom import minidom

articles = []

while i < 525900:
    i = 525707

    f = urllib.urlopen("http://www.thecrimson.com/article.aspx?ref=%i" % i)
    dom = minidom.parse(f)
    f.close()
    n = dom.getElementById('ArticleBody')
    articles.append({
        'text': ,
        'headline': n.getElementById(Headline).data,
        'subheadline': ,
        'date': ,
    })
    