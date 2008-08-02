from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.core import serializers
from crimsononline.admin.admin_forms import ArticleForm
from crimsononline.core.models import Article, Contributor

def edit_article(request, article_id=None):
	
	# add article
	if article_id == None:
		form = ArticleForm()
		
	else:
		# edit article
		if request.method != 'POST':
			article_id = int(article_id)
			a = get_object_or_404(Article, pk=article_id)
			form = ArticleForm(instance=a)
			choices = []
			# insert contributors into contributors field
			# (we don't want all 500 contributors, only the right ones)
			for contributor in a.contributors.all():
				s = "%s %s %s" % (contributor.first_name, 
									contributor.middle_initial, 
									contributor.last_name)
				choices.append((contributor.id, s))
			form.contributors.widget.choices = tuple(choices)
		# save article
		else:
			form = ArticleForm(request.POST)
			try:
				form.save()
				return HttpResponseRedirect('/admin/core/article/%s' % article_id)
			except ValueError:
				pass		
		
	return render_to_response('edit_article.html', {'form': form})

def get_contributor(request):
	if request.method == "GET":
		q = request.GET.get('q', '')
		if len(q) < 3:
			return HttpResponse('')
		else:
			contributors = Contributor.objects.filter(first_name__icontains=q) | \
							Contributor.objects.filter(last_name__icontains=q)
			data = ''
			for c in contributors:
				data += str(c.id) + '|' + c.first_name + '|' + \
						c.middle_initial + '|' + c.last_name + '\n'
			return HttpResponse(data)