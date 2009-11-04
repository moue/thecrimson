from haystack import site
from haystack import indexes
from crimsononline.content.models import Article

class ArticleIndex(indexes.SearchIndex):
	text = indexes.CharField(document=True, model_attr='teaser', use_template=True)
	pub_date = indexes.DateTimeField(model_attr='issue__issue_date')
	

site.register(Article, ArticleIndex)
