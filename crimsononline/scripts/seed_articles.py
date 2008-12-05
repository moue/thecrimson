import urllib
f = urllib.urlopen("http://www.thecrimson.com/article.aspx?ref=525707")
s = f.read()
f.close()

""" look here: http://www.boddie.org.uk/python/HTML.html """