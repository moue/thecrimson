from django.contrib.sitemaps import Sitemap
from crimsononline.content.models import Article

class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Article.objects.filter(pub_status=1)

    def lastmod(self, obj):
        return obj.modified_on
