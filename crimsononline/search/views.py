from haystack.views import SearchView
from django.shortcuts import render_to_response
from haystack.query import SearchQuerySet
from crimsononline.content.models import Contributor, Tag

class AjaxSearchView(SearchView):
    
    def create_response(self):
        """
        Generates the actual HttpResponse to send back to the user.
        """
        
        q =  self.request.GET.get('q','')
        if q:
            contributors_qs = SearchQuerySet().models(Contributor)
            tags_qs = SearchQuerySet().models(Tag)
            matching_contributors = contributors_qs.auto_query(q)
            matching_tags = tags_qs.auto_query(q)
        else:
            matching_contributors = None
            matching_tags = None
        
        (paginator, page) = self.build_page()
        
        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
            'contributors': matching_contributors,
            'tags': matching_tags,
        }
        context.update(self.extra_context())

        if self.request.GET.has_key('ajax'):
            t = 'ajax/search_results_page.html'
        else:
            t = self.template
        return render_to_response(t, context, context_instance=self.context_class(self.request))
        
    