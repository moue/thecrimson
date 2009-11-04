import datetime
from haystack import site
from haystack import indexes
from crimsononline.content.models import Article

class ArticleIndex(indexes.SearchIndex):
	text = indexes.CharField(document=True, model_attr='teaser', use_template=True)
	pub_date = indexes.DateTimeField(model_attr='issue__issue_date')
	
	def get_queryset(self):
		"Used when the entire index for model is updated."
		return Article.objects.filter(issue__issue_date__gte=datetime.date(2009,1,1))

site.register(Article, ArticleIndex)
