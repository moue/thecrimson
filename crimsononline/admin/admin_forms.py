from django import newforms as forms
from crimsononline.core.models import Article, Contributor

#========== forms ================

#form for editing / adding articles
class ArticleForm(forms.ModelForm):
	headline = forms.CharField(widget=forms.TextInput(attrs={'size': 50}))
	subheadline = forms.CharField(widget=forms.TextInput(attrs={'size': 50}))
	text = forms.CharField(widget=forms.Textarea(attrs={'rows': 40, 'cols': 80}))
	
	#start out with no contributors (they'll be added by Javascript)
	contributors = forms.ModelMultipleChoiceField(queryset=Contributor.objects.filter(first_name__exact=None))

	class Meta:
		model = Article
